"""Domain chat: projects, fork, context (needs DATABASE_URL)."""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from unittest.mock import patch

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.models import ChatSession, Message, Project, User
from app.db.session import get_engine
from app.main import app
from app.services import chat_sessions as chat_svc
from app.services import messages as messages_svc
from app.services import projects as projects_svc
from app.services.errors import ConflictError, ForbiddenError

load_dotenv()

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="DATABASE_URL required",
)


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    get_settings.cache_clear()
    import app.db.session as db_session

    db_session._engine = None
    db_session._SessionLocal = None
    SessionLocal = sessionmaker(
        bind=get_engine(), autoflush=False, autocommit=False
    )
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def user(db: Session) -> User:
    email = f"chat-test-{uuid.uuid4().hex[:8]}@example.com"
    u = User(email=email, email_verified=True, name="Chat Tester", status="active")
    db.add(u)
    db.commit()
    db.refresh(u)
    yield u
    # cleanup: subs first (FK to messages), then messages, mains, projects, user
    subs = db.scalars(
        select(ChatSession).where(
            ChatSession.user_id == u.id,
            ChatSession.is_main.is_(False),
        )
    ).all()
    for s in subs:
        db.execute(delete(Message).where(Message.session_id == s.id))
        db.delete(s)
    db.flush()
    mains = db.scalars(
        select(ChatSession).where(
            ChatSession.user_id == u.id,
            ChatSession.is_main.is_(True),
        )
    ).all()
    for s in mains:
        db.execute(delete(Message).where(Message.session_id == s.id))
        db.delete(s)
    db.flush()
    db.execute(delete(Project).where(Project.user_id == u.id))
    db.execute(delete(User).where(User.id == u.id))
    db.commit()


def test_project_immutable_link_and_delete_conflict(db: Session, user: User) -> None:
    project = projects_svc.create_project(db, user.id, name="P1", icon="code")
    db.commit()
    db.refresh(project)
    assert project.icon == "code"

    session = chat_svc.create_main_session(
        db, user.id, title="S1", project_id=project.id
    )
    db.commit()
    assert session.project_id == project.id

    with pytest.raises(ConflictError):
        projects_svc.delete_project(db, user.id, project.id)


def test_project_icon_default_and_patch(db: Session, user: User) -> None:
    project = projects_svc.create_project(db, user.id, name="icons")
    db.commit()
    db.refresh(project)
    assert project.icon == "folder"

    updated = projects_svc.update_project(db, user.id, project.id, icon="rocket")
    db.commit()
    assert updated.icon == "rocket"


def test_fork_and_context_assembly(db: Session, user: User) -> None:
    import time

    main = chat_svc.create_main_session(db, user.id, title="main")
    m1 = messages_svc.add_message(db, main, role="user", content="hello")
    time.sleep(0.02)
    m2 = messages_svc.add_message(db, main, role="assistant", content="hi")
    time.sleep(0.02)
    messages_svc.add_message(db, main, role="user", content="later")
    db.commit()

    sub = chat_svc.fork_subsession(
        db, user.id, main.id, forked_from_message_id=m2.id, title="branch"
    )
    messages_svc.add_message(db, sub, role="user", content="branch q")
    db.commit()

    ctx = chat_svc.assemble_context_messages(db, sub)
    texts = [m.content for m in ctx]
    assert texts == ["hello", "hi", "branch q"]
    assert "later" not in texts

    with pytest.raises(ForbiddenError):
        chat_svc.fork_subsession(
            db, user.id, sub.id, forked_from_message_id=m1.id
        )


def test_edit_latest_stays_on_main(db: Session, user: User) -> None:
    main = chat_svc.create_main_session(db, user.id)
    u1 = messages_svc.add_message(db, main, role="user", content="old")
    db.commit()
    target_session, msg = messages_svc.prepare_edit_target(
        db, user.id, main.id, u1.id, new_content="new"
    )
    db.commit()
    assert target_session.id == main.id
    assert msg.id == u1.id
    assert msg.content == "new"


def test_edit_old_forks_subsession(db: Session, user: User) -> None:
    main = chat_svc.create_main_session(db, user.id)
    u1 = messages_svc.add_message(db, main, role="user", content="first")
    messages_svc.add_message(db, main, role="assistant", content="resp")
    messages_svc.add_message(db, main, role="user", content="second")
    db.commit()
    target_session, msg = messages_svc.prepare_edit_target(
        db, user.id, main.id, u1.id, new_content="first-edited"
    )
    db.commit()
    assert target_session.is_main is False
    assert target_session.parent_session_id == main.id
    assert msg.content == "first-edited"


def test_api_requires_auth() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/projects").status_code == 401
    assert client.get("/api/v1/chat/sessions").status_code == 401


async def _fake_agent_events(**kwargs):
    yield {
        "event": "step_started",
        "data": {
            "step_id": "1",
            "kind": "route",
            "name": "orchestrator",
            "title": "orchestrator",
        },
    }
    yield {
        "event": "step_finished",
        "data": {
            "step_id": "1",
            "kind": "route",
            "name": "orchestrator",
            "status": "ok",
            "summary": "route=direct",
        },
    }
    yield {
        "event": "message_completed",
        "data": {
            "content": "hello from mock",
            "run_id": "run-1",
            "steps": [
                {
                    "step_id": "1",
                    "kind": "route",
                    "name": "orchestrator",
                    "status": "ok",
                }
            ],
        },
    }


def test_sse_message_with_mocked_agent(db: Session, user: User) -> None:
    main = chat_svc.create_main_session(db, user.id, title="sse")
    db.commit()

    from app.api.deps import get_current_user
    from app.db.session import get_db

    def override_user():
        return user

    def override_db():
        yield db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    try:
        with patch(
            "app.services.chat_runs.iter_agent_events",
            new=_fake_agent_events,
        ):
            client = TestClient(app)
            with client.stream(
                "POST",
                f"/api/v1/chat/sessions/{main.id}/messages",
                json={"content": "hi agent"},
            ) as resp:
                assert resp.status_code == 200
                body = "".join(resp.iter_text())
            assert "event: run_started" in body
            assert "event: step_started" in body
            assert "event: message_completed" in body
            assert "hello from mock" in body
            assert "event: done" in body
            assert "event: session_updated" not in body
    finally:
        app.dependency_overrides.clear()

    db.expire_all()
    db.refresh(main)
    assert main.run_status == "completed"
    assert main.active_run_id is None
    msgs = chat_svc.list_session_messages(db, main)
    assert any(m.role == "assistant" and m.content == "hello from mock" for m in msgs)


def test_sse_autotitle_on_first_message(db: Session, user: User) -> None:
    main = chat_svc.create_main_session(db, user.id, title=None)
    db.commit()

    from app.api.deps import get_current_user
    from app.db.session import get_db

    def override_user():
        return user

    def override_db():
        yield db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    try:
        with (
            patch(
                "app.services.chat_runs.iter_agent_events",
                new=_fake_agent_events,
            ),
            patch(
                "app.services.chat_runs.generate_session_title",
                return_value="API login JWT",
            ),
        ):
            client = TestClient(app)
            with client.stream(
                "POST",
                f"/api/v1/chat/sessions/{main.id}/messages",
                json={"content": "Viết giúp tôi một API login bằng JWT"},
            ) as resp:
                assert resp.status_code == 200
                body = "".join(resp.iter_text())
            assert "event: session_updated" in body
            assert "API login JWT" in body
    finally:
        app.dependency_overrides.clear()

    db.expire_all()
    db.refresh(main)
    assert main.title == "API login JWT"


def test_list_sessions_pagination(db: Session, user: User) -> None:
    for i in range(5):
        chat_svc.create_main_session(db, user.id, title=f"s{i}")
    db.commit()

    page1, more1 = chat_svc.list_main_sessions_page(
        db, user.id, limit=2, offset=0
    )
    assert more1 is True
    assert len(page1) == 2

    page2, more2 = chat_svc.list_main_sessions_page(
        db, user.id, limit=2, offset=2
    )
    assert more2 is True
    assert len(page2) == 2
    assert {s.id for s in page1}.isdisjoint({s.id for s in page2})

    page3, more3 = chat_svc.list_main_sessions_page(
        db, user.id, limit=2, offset=4
    )
    assert more3 is False
    assert len(page3) == 1


def test_pin_session_limit_three(db: Session, user: User) -> None:
    s1 = chat_svc.create_main_session(db, user.id, title="p1")
    s2 = chat_svc.create_main_session(db, user.id, title="p2")
    s3 = chat_svc.create_main_session(db, user.id, title="p3")
    s4 = chat_svc.create_main_session(db, user.id, title="p4")
    db.commit()

    chat_svc.pin_session(db, user.id, s1.id)
    chat_svc.pin_session(db, user.id, s2.id)
    chat_svc.pin_session(db, user.id, s3.id)
    db.commit()

    with pytest.raises(ConflictError):
        chat_svc.pin_session(db, user.id, s4.id)

    # idempotent pin
    again = chat_svc.pin_session(db, user.id, s1.id)
    assert again.is_pinned is True

    chat_svc.unpin_session(db, user.id, s2.id)
    db.commit()
    pinned = chat_svc.pin_session(db, user.id, s4.id)
    db.commit()
    assert pinned.is_pinned is True
    assert pinned.pinned_at is not None

    listed = chat_svc.list_main_sessions(db, user.id)
    assert listed[0].is_pinned is True
    assert listed[1].is_pinned is True
    assert listed[2].is_pinned is True
    pinned_ids = {s.id for s in listed if s.is_pinned}
    assert pinned_ids == {s1.id, s3.id, s4.id}


def test_last_message_at_tracks_main_and_sub(db: Session, user: User) -> None:
    main = chat_svc.create_main_session(db, user.id, title="lm")
    db.commit()
    assert main.last_message_at is None

    messages_svc.add_message(db, main, role="user", content="on main")
    db.commit()
    db.refresh(main)
    assert main.last_message_at is not None

    m1 = messages_svc.add_message(db, main, role="assistant", content="ok")
    db.commit()
    db.refresh(main)
    main_ts = main.last_message_at
    assert main_ts is not None

    sub = chat_svc.fork_subsession(
        db, user.id, main.id, forked_from_message_id=m1.id, title="branch"
    )
    db.commit()
    db.refresh(main)
    # Fork alone không đổi last_message_at của main.
    assert main.last_message_at == main_ts

    messages_svc.add_message(db, sub, role="user", content="on sub")
    db.commit()
    db.refresh(main)
    db.refresh(sub)
    assert sub.last_message_at is not None
    assert main.last_message_at is not None
    assert main.last_message_at >= sub.last_message_at
    assert main.last_message_at > main_ts


def test_mark_read_and_has_unread(db: Session, user: User) -> None:
    main = chat_svc.create_main_session(db, user.id, title="read")
    db.commit()
    assert chat_svc.session_has_unread(db, main) is False

    messages_svc.add_message(db, main, role="user", content="q")
    messages_svc.add_message(db, main, role="assistant", content="a")
    db.commit()
    db.refresh(main)
    assert chat_svc.session_has_unread(db, main) is True

    chat_svc.mark_session_read(db, user.id, main.id)
    db.commit()
    db.refresh(main)
    assert chat_svc.session_has_unread(db, main) is False

    from app.api.deps import get_current_user
    from app.db.session import get_db

    def override_user():
        return user

    def override_db():
        yield db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        resp = client.post(f"/api/v1/chat/sessions/{main.id}/read")
        assert resp.status_code == 200
        body = resp.json()
        assert body["has_unread"] is False
        assert body["run_status"] in {"idle", "completed", "error", "running"}
        assert "last_read_at" in body
    finally:
        app.dependency_overrides.clear()


def test_concurrent_run_returns_409(db: Session, user: User) -> None:
    from app.services import chat_runs as chat_runs_svc
    from app.services.chat_runs import ChatRun

    main = chat_svc.create_main_session(db, user.id, title="busy")
    run_id = uuid.uuid4()
    main.run_status = "running"
    main.active_run_id = run_id
    db.commit()

    # Giữ run trong memory để heal không coi là stale.
    chat_runs_svc._runs[str(run_id)] = ChatRun(
        run_id=run_id,
        session_id=main.id,
        user_id=user.id,
        user_message_id=uuid.uuid4(),
    )

    from app.api.deps import get_current_user
    from app.db.session import get_db

    def override_user():
        return user

    def override_db():
        yield db

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_db] = override_db
    try:
        client = TestClient(app)
        resp = client.post(
            f"/api/v1/chat/sessions/{main.id}/messages",
            json={"content": "second"},
        )
        assert resp.status_code == 409
    finally:
        app.dependency_overrides.clear()
        chat_runs_svc._runs.clear()
