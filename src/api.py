"""
api.py — FastAPI HTTP server wrapping the Workday Router brain.

Run with:
    .venv\\Scripts\\python.exe -m uvicorn src.api:app --reload --port 8000

Then open: http://localhost:8000/docs  (Swagger UI)
"""

import json
import os
import sys
import time
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# ── Path setup ────────────────────────────────────────────────────────────────
_HERE        = os.path.dirname(os.path.abspath(__file__))        # src/
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, ".."))       # project root

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

# Non-interactive mode — no browser popups
os.environ["WORKDAY_NON_INTERACTIVE"] = "true"

# ── Brain import ──────────────────────────────────────────────────────────────
from src.supervisor import run_intelligent_supervisor, _get_brain  # noqa: E402


# ── Query logging ─────────────────────────────────────────────────────────────
# Every /ask call gets appended here as one JSON line: query, plan, RAG matches
# (including top-k candidates, not just the winner), answer, and any error.
# This is what you hand back for review instead of pasting responses manually.
LOG_PATH = Path(_PROJECT_ROOT) / "test_logs" / "query_log.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def _log_query(query, plan=None, rag_matches=None, answer=None, error=None):
    entry = {
        "timestamp": time.time(),
        "query": query,
        "plan": plan,
        "rag_matches": rag_matches or [],
        "answer": answer,
        "error": error,
    }
    try:
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as log_exc:
        # Logging should never break the actual request.
        print(f"[API] WARNING: failed to write query log: {log_exc}")


# ── Lifespan: token refresh on startup ───────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Refresh Workday token on startup, then start 30-min background timer."""
    print("[API] Starting up — refreshing Workday token...")
    try:
        from src.tools.Refresh_token import force_refresh
        force_refresh()
        print("[API] Token refreshed successfully.")
    except Exception as exc:
        print(f"[API] WARNING: Token refresh on startup failed: {exc}")

    # Start the 30-minute background refresh timer
    import threading, time as _time
    def _timer():
        while True:
            _time.sleep(1800)
            try:
                from src.tools.Refresh_token import force_refresh
                force_refresh()
                print("[API] Background token refresh successful.")
            except Exception as exc:
                print(f"[API] Background token refresh failed: {exc}")

    threading.Thread(target=_timer, daemon=True).start()

    yield  # server is running


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Workday Router API",
    description="Natural-language interface to Workday REST & SOAP APIs via a RAG-powered brain.",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────




from pydantic import BaseModel, Field


class AskPayload(BaseModel):
    query: str
    history: list[dict] = Field(default_factory=list)
    debug: bool = True


def _process_ask(query: str, history: list = None, debug: bool = True):
    plan = None
    context = None

    try:
        planner, executor, synthesizer = _get_brain()
        plan = planner.plan(query, history=history)

        if plan.get("status") == "needs_clarification":
            clarification = plan.get("clarification_question", "Could you please clarify your request?")
            _log_query(query, plan=plan, answer=clarification)
            res = {"answer": clarification, "rag_matches": []}
            if debug:
                res["plan"] = plan
            return res

        if not plan or "steps" not in plan:
            _log_query(query, plan=plan, error="Planner failed to generate a valid execution plan.")
            raise HTTPException(status_code=400, detail="Planner failed to generate a valid execution plan.")

        # Block write operations from this read-only endpoint
        has_write = any(
            step.get("method", "GET").upper() != "GET"
            for step in plan.get("steps", [])
        )
        if has_write:
            _log_query(query, plan=plan, error="Write operation blocked on read-only endpoint.")
            raise HTTPException(
                status_code=400,
                detail="This query requires a write operation, which is not supported by this API.",
            )

        context = executor.run(plan)
        answer = synthesizer.synthesize(
            user_query=query,
            plan=plan,
            context=context,
        )

        rag_matches = []
        for step_key, step_result in context.items():
            if isinstance(step_result, dict) and "rag_route" in step_result:
                rag_matches.append({
                    "step": step_key,
                    "matched_route": step_result.get("rag_route"),
                    "api_name": step_result.get("api_name"),
                    "confidence_score": step_result.get("confidence_score"),
                    "top_k_candidates": step_result.get("top_k_candidates"),
                    "executed_url": step_result.get("api_called"),
                })

        try:
            parsed_answer = json.loads(answer)
        except (json.JSONDecodeError, TypeError):
            parsed_answer = answer

        _log_query(query, plan=plan, rag_matches=rag_matches, answer=parsed_answer)

        result = {
            "answer": parsed_answer,
            "rag_matches": rag_matches,
        }
        if debug:
            result["plan"] = plan
            result["raw_context"] = context

        return result

    except HTTPException:
        raise
    except Exception as exc:
        print(f"[API] /ask failed for query='{query}': {exc}")
        _log_query(query, plan=plan, error=str(exc))
        raise HTTPException(status_code=500, detail="Internal error processing query.")


@app.get("/ask", tags=["Read"])
def ask_workday_get(query: str, debug: bool = True):
    return _process_ask(query=query, history=None, debug=debug)


@app.post("/ask", tags=["Read"])
def ask_workday_post(payload: AskPayload):
    return _process_ask(query=payload.query, history=payload.history, debug=payload.debug)


@app.get("/plan", tags=["Debug"])
def preview_plan(query: str):
    """
    Preview the execution plan for a query without running it.
    Useful for debugging what the Planner LLM will do.
    """
    try:
        planner, _, _ = _get_brain()
        plan = planner.plan(query)
        return plan
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/history", tags=["History"])
def get_query_history():
    """Returns the last 20 queries from the log file."""
    if not LOG_PATH.exists():
        return []
    try:
        logs = []
        with open(LOG_PATH, "r") as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
        # Return last 20 records, reversed (most recent first)
        return logs[-20:][::-1]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read query logs: {str(exc)}")


@app.get("/me", tags=["User"])
def get_current_user():
    """
    Returns the current authenticated Workday user profile (name, title, initials).
    """
    try:
        _, executor, _ = _get_brain()
        me_plan = {
            "goal": "Get current user profile",
            "steps": [{
                "id": 1,
                "intent": "Fetch current user profile",
                "api_type": "rest",
                "api_hint": "get current user profile",
                "query_params": {},
                "path_params": {"ID": "me"},
                "extract_fields": ["descriptor", "name", "businessTitle"]
            }]
        }
        context = executor.run(me_plan)
        step1 = context.get("step_1", {})
        extracted = step1.get("extracted", {})

        name = extracted.get("descriptor") or extracted.get("name") or "Logan McNeil"
        title = extracted.get("businessTitle") or extracted.get("title") or "Vice President, Human Resources"
        first_name = name.split()[0] if name else "Logan"

        parts = [p for p in name.split() if p and not p.startswith("[")]
        if len(parts) >= 2:
            initials = (parts[0][0] + parts[-1][0]).upper()
        elif len(parts) == 1:
            initials = parts[0][:2].upper()
        else:
            initials = "LM"

        return {
            "name": name,
            "first_name": first_name,
            "title": title,
            "initials": initials
        }
    except Exception as exc:
        print(f"[API] /me fallback due to error: {exc}")
        return {
            "name": "Logan McNeil",
            "first_name": "Logan",
            "title": "Vice President, Human Resources",
            "initials": "LM"
        }


# Serve WorkPulse_UI directly
ui_dir = Path(_PROJECT_ROOT) / "WorkPulse_UI"
ui_dir.mkdir(parents=True, exist_ok=True)

app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="static")