"""CoinGecko: global market + DeFi global."""

from __future__ import annotations

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from agent.tools.coingecko.client import coingecko_get, to_tool_result
from agent.tools.coingecko.descriptions import GLOBAL


class GlobalInput(BaseModel):
    kind: str = Field(
        default="crypto",
        description="crypto = /global | defi = /global/decentralized_finance_defi",
    )


def fetch_global(kind: str = "crypto") -> str:
    """Gọi /global hoặc /global/decentralized_finance_defi."""
    key = (kind or "crypto").strip().lower()
    if key in {"defi", "decentralized_finance_defi"}:
        data = coingecko_get("/global/decentralized_finance_defi")
        return to_tool_result({"kind": "defi", "data": data})

    data = coingecko_get("/global")
    return to_tool_result({"kind": "crypto", "data": data.get("data", data)})


def get_coingecko_global_tool() -> StructuredTool:
    return StructuredTool.from_function(
        name="coingecko_global",
        description=GLOBAL,
        func=fetch_global,
        args_schema=GlobalInput,
    )
