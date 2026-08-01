"""
AutoSOC live dashboard backend.

Hooks into CrewAI's event bus to get real, granular updates as the crew
runs (agent started/finished, tool calls, tool results) and streams them
to the browser over Server-Sent Events. Nothing here is simulated, every
event on the dashboard corresponds to something the crew actually did.
"""

import asyncio
import json
import os
import queue
import sys
import threading
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# make sure `src` resolves regardless of where uvicorn is launched from
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, UploadFile, File  # noqa: E402
from fastapi.responses import FileResponse, StreamingResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from crewai.events import crewai_event_bus  # noqa: E402
from crewai.events.types.agent_events import (  # noqa: E402
    AgentExecutionCompletedEvent,
    AgentExecutionStartedEvent,
)
from crewai.events.types.tool_usage_events import (  # noqa: E402
    ToolUsageFinishedEvent,
    ToolUsageStartedEvent,
)

from src.crew import run_soc_crew  # noqa: E402

app = FastAPI()

event_queue: "queue.Queue" = queue.Queue()

state = {
    "agents": {"Mon": "idle", "Searcher": "idle", "Scribe": "idle"},
    "alerts": [],
    "report": None,
    "running": False,
    "error": None,
}

# maps the verbose CrewAI agent role string back to a short dashboard label
AGENT_LABELS = {
    "SOC Tier 1 Analyst - Log Monitor": "Mon",
    "SOC Tier 2 Analyst - Threat Investigator": "Searcher",
    "SOC Reporting Analyst": "Scribe",
}


def label_for(role: str) -> str:
    return AGENT_LABELS.get(role, role or "System")


def role_of(event) -> str:
    """CrewAI's agent_role field on events isn't reliably populated in
    this version, event.agent.role is. Fall back gracefully either way."""
    agent = getattr(event, "agent", None)
    if agent is not None and getattr(agent, "role", None):
        return agent.role
    return getattr(event, "agent_role", None) or "System"


def push(event: dict):
    event["ts"] = datetime.now().strftime("%H:%M:%S")
    event_queue.put(event)


@crewai_event_bus.on(AgentExecutionStartedEvent)
def _on_agent_started(source, event):
    label = label_for(role_of(event))
    state["agents"][label] = "running"
    push({"type": "agent_status", "agent": label, "status": "running"})
    push({"type": "log", "agent": label, "text": f"{label} agent started", "level": "info"})


@crewai_event_bus.on(AgentExecutionCompletedEvent)
def _on_agent_completed(source, event):
    label = label_for(role_of(event))
    state["agents"][label] = "done"
    push({"type": "agent_status", "agent": label, "status": "done"})
    push({"type": "log", "agent": label, "text": f"{label} agent finished", "level": "info"})


@crewai_event_bus.on(ToolUsageStartedEvent)
def _on_tool_started(source, event):
    label = label_for(role_of(event))
    push({
        "type": "log",
        "agent": label,
        "text": f"{label} -> calling {event.tool_name}({str(event.tool_args)[:120]})",
        "level": "tool",
    })


@crewai_event_bus.on(ToolUsageFinishedEvent)
def _on_tool_finished(source, event):
    label = label_for(role_of(event))
    output = str(event.output)
    is_alert = "MATCH FOUND" in output
    push({
        "type": "log",
        "agent": label,
        "text": f"{event.tool_name} -> {output[:200]}",
        "level": "alert" if is_alert else "result",
    })
    if is_alert:
        state["alerts"].append(output[:200])
        push({"type": "alert", "agent": label, "text": output[:200]})


def _run_crew_job(log_files):
    state["running"] = True
    state["error"] = None
    state["report"] = None
    state["alerts"] = []
    for k in state["agents"]:
        state["agents"][k] = "idle"
    push({"type": "run_started"})
    try:
        result = run_soc_crew(log_files)
        state["report"] = result
        push({"type": "run_completed", "report": result})
    except Exception as e:  # surface the real error to the dashboard
        state["error"] = str(e)
        for k in state["agents"]:
            if state["agents"][k] == "running":
                state["agents"][k] = "idle"
        push({"type": "run_failed", "error": str(e)})
    finally:
        state["running"] = False


@app.post("/api/run")
async def trigger_run():
    if state["running"]:
        return {"ok": False, "error": "A scan is already running"}
    log_files = ["sample_logs/auth.log", "sample_logs/network.log"]
    thread = threading.Thread(target=_run_crew_job, args=(log_files,), daemon=True)
    thread.start()
    return {"ok": True}


@app.post("/api/upload")
async def upload_log(file: UploadFile = File(...)):
    if state["running"]:
        return {"ok": False, "error": "A scan is already running"}
    uploads_dir = os.path.join(PROJECT_ROOT, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    safe_name = os.path.basename(file.filename or "upload.log")
    dest = os.path.join(uploads_dir, safe_name)
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    push({"type": "log", "agent": "System", "text": f"Uploaded log: {safe_name} ({len(content)} bytes)", "level": "info"})
    thread = threading.Thread(target=_run_crew_job, args=([dest],), daemon=True)
    thread.start()
    return {"ok": True, "filename": safe_name}


@app.get("/api/status")
async def get_status():
    return state


@app.get("/api/events")
async def stream_events():
    async def gen():
        while True:
            try:
                event = event_queue.get_nowait()
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                await asyncio.sleep(0.3)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/")
async def index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)
