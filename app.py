import os
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from router import demo_provider, groq, load_cases, run

app = FastAPI(title="ModelRouter", version="0.1.0")
demo = demo_provider(load_cases())


class RouteRequest(BaseModel):
    task: Literal["classify", "extract_order", "calculate"]
    text: str = Field(min_length=1, max_length=3000, pattern=r"\S")
    strategy: Literal["router", "baseline"] = "router"


@app.post("/route")
def route(payload: RouteRequest):
    live = bool(os.environ.get("GROQ_API_KEY", "").strip())
    result = run(payload.task, payload.text, payload.strategy, groq if live else demo)
    result["mode"] = "live" if live else "demo"
    if not live:
        result["latency_ms"] = None
    return JSONResponse(result, status_code=200 if result["ok"] else 422 if result["error"] == "demo_case_not_found" else 502)
