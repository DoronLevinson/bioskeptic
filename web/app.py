import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from web import agent

app = FastAPI()
WEB = Path(__file__).parent

# Serve static assets (logo, stylesheet, script) from web/static/ at /static/…
app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")


class ChatIn(BaseModel):
    messages: list[dict]  # full history each turn (the server keeps no state)


@app.get("/")
def index():
    # no-store: during development, don't let the browser serve a stale cached page (else its old JS
    # can mismatch the current /chat response format — e.g. calling res.json() on the SSE stream).
    return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-store"})


# Stream the turn as Server-Sent Events (SSE): one "data: {json}\n\n" line per agent event.
# The browser reads these live to show the status line, then renders the final reply.
@app.post("/chat")
def chat(body: ChatIn):
    def sse():
        for event in agent.stream_events(body.messages):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")
