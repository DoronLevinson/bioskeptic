import json
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from web import agent, guard

app = FastAPI()
WEB = Path(__file__).parent

# Serve static assets (logo, stylesheet, script) from web/static/ at /static/…
app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")


# Make browsers revalidate the JS/CSS on every load (cheap 304s via the file's ETag) so a new deploy
# shows up without a hard refresh — otherwise the cached app.js/style.css hide the update.
@app.middleware("http")
async def revalidate_static(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


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
def chat(body: ChatIn, request: Request):
    ok, note = guard.allow(guard.client_ip(request))
    if not ok:
        def blocked():
            yield f"data: {json.dumps({'type': 'reply', 'text': note})}\n\n"
        return StreamingResponse(blocked(), media_type="text/event-stream")

    def sse():
        for event in agent.stream_events(body.messages):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")
