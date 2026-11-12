"""Path `$stepN.*` theo từng tool — tách khỏi tool description/catalog."""

from __future__ import annotations

# name → block mô tả path (N = index bước trong plan, bắt đầu 0)
TOOL_RESULT_PATHS: dict[str, str] = {
    "time_now": (
        "$stepN.now.date_dmy | $stepN.now.date | $stepN.now.iso | "
        "$stepN.now.iso_utc | $stepN.now.unix | $stepN.now.timezone | $stepN.now.time\n"
        "  (date = YYYY-MM-DD; date_dmy = DD-MM-YYYY)"
    ),
    "time_convert": (
        "$stepN.to.date_dmy | $stepN.to.date | $stepN.to.iso | "
        "$stepN.from.date_dmy | $stepN.from.iso | $stepN.input"
    ),
    "time_shift": (
        "$stepN.result.date_dmy | $stepN.result.date | $stepN.result.iso | "
        "$stepN.base.date_dmy | $stepN.base.iso | $stepN.delta.days"
    ),
    "tavily_search": (
        "$stepN.answer | $stepN.results.0.title | $stepN.results.0.url | "
        "$stepN.results.0.content | $stepN.query"
    ),
    "tavily_extract": (
        "$stepN.content | $stepN.title | $stepN.url"
    ),
    "calc_evaluate": (
        "$stepN.numeric | $stepN.symbolic | $stepN.latex | $stepN.expression"
    ),
    "calc_solve": (
        "$stepN.solutions.0 | $stepN.solutions_numeric.0 | "
        "$stepN.variable | $stepN.equation"
    ),
    "calc_diff": (
        "$stepN.symbolic | $stepN.latex | $stepN.variable | $stepN.order"
    ),
    "calc_integrate": (
        "$stepN.numeric | $stepN.symbolic | $stepN.latex | "
        "$stepN.definite | $stepN.variable"
    ),
    "calc_percent_change": (
        "$stepN.percent_change | $stepN.absolute_change | $stepN.old | $stepN.new"
    ),
    "document_to_markdown": (
        "$stepN.markdown | $stepN.source_path | $stepN.source_type | "
        "$stepN.char_count | $stepN.output_path | $stepN.pages.0"
    ),
}


def tool_result_paths_text(tool_names: list[str] | None = None) -> str:
    """Catalog path kết quả; mặc định theo tool đang đăng ký trong get_tools()."""
    if tool_names is None:
        from agent.tools import get_tools

        tool_names = [t.name for t in get_tools()]

    blocks: list[str] = []
    for name in tool_names:
        paths = TOOL_RESULT_PATHS.get(name)
        if not paths:
            continue
        blocks.append(f"- {name}:\n  {paths}")
    return "\n\n".join(blocks) if blocks else "(không có path)"


__all__ = ["TOOL_RESULT_PATHS", "tool_result_paths_text"]
