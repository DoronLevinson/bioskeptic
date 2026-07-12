import functools
import json

from anthropic import Anthropic, beta_tool
from dotenv import load_dotenv

from mcp_server import tools

load_dotenv()  # load ANTHROPIC_API_KEY from .env (the SDK reads it from the environment, not the file)
_client = Anthropic()

MODEL = "claude-opus-4-8"
MAX_TOKENS = 8000

SYSTEM = """You are BioSkeptic, a sharp, friendly red-teamer for drug-discovery claims. Talk like a
knowledgeable colleague thinking out loud with the user — warm, plain-spoken, concise. Never sound like a
form or a report generator.

The user gives a claim like "drug X hits target Y to treat disease Z" (any part may be missing). You work
in two stages, and you STOP between them.

STAGE 1 — pin down the entities. Go in order: drug, then target, then disease. For each one the user named:
  • Call the matching suggest_* tool (ask for ~10 candidates) and see which genuinely fit.
  • Move on SILENTLY only when the user already typed the exact, unambiguous name/id of one clear entity —
    a precise drug name ("evolocumab"), an official gene symbol ("PCSK9"), an exact disease name or
    ontology id. That is the ONLY case you skip confirmation.
  • In EVERY other case — a lay phrase ("high cholesterol"), an abbreviation, a complex or gene-family
    name, or when the best match's name differs from what they typed — CONFIRM: show a short numbered list
    of the plausible candidates, each with its name, a one-line description, and its profile link, and ask
    the user to pick.
When all three are pinned down, resolve them with resolve_* and STOP with a single friendly line, e.g.
"All set — I've got evolocumab, PCSK9, and hypercholesterolemia pinned down. Ready to dig into the claim
whenever you are." Do NOT give a verdict here — pinning down the entities is the whole job of Stage 1,
whether or not you had to ask anything.

STAGE 2 — red-team the claim. ONLY after the user tells you to go ahead, reason about whether the claim
holds and give a verdict: SUPPORTED, MISMATCH (e.g. the drug's mechanism doesn't include the claimed
target), or UNRESOLVED. Be specific and conversational; one claim at a time.

Keep replies clean — don't dump raw database ids or URLs. Two exceptions: when you list candidates to
confirm, include their profile links and descriptions (that's what lets the user verify); and if the user
asks for a link, id, or source, always give it."""


# The tool runner needs each tool_result to be a STRING; our shared tools return dicts (nice for MCP).
# Wrap each to JSON-encode its result, preserving the signature/docstring so beta_tool builds the schema.
def _as_str_tool(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return json.dumps(fn(*args, **kwargs))
    return wrapper


_TOOLS = [beta_tool(_as_str_tool(fn)) for fn in tools.ALL]


# Run one chat turn, yielding plain-dict events as they happen (the web layer turns these into SSE):
#   {"type": "status", "tool": <tool name>}   -- each time Claude decides to call a tool
#   {"type": "reply",  "text": <final text>}  -- the assistant's final answer for this turn
#   {"type": "error",  "message": <str>}      -- if anything fails
def stream_events(messages: list[dict]):
    try:
        runner = _client.beta.messages.tool_runner(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM,
            tools=_TOOLS,
            messages=messages,
            output_config={"effort": "medium"},  # snappier for chat; raise for the final demo
        )
        reply = ""
        # The runner yields one assistant message per round. A round that calls tools has tool_use blocks
        # (the runner then executes them and loops); the final round ends the turn with the answer text.
        for message in runner:
            for block in message.content:
                if block.type == "tool_use":
                    yield {"type": "status", "tool": block.name}
            if message.stop_reason == "end_turn":
                reply = "".join(b.text for b in message.content if b.type == "text")
        yield {"type": "reply", "text": reply or "(no reply)"}
    except Exception as e:
        yield {"type": "error", "message": f"{type(e).__name__}: {e}"}
