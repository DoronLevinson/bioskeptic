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
  • Call the matching suggest_* tool (~10 candidates) to SEE the ranked options with their one-line
    descriptions and links. Do this even for a clean-looking name — the top raw resolve is often a wrong
    subtype (e.g. resolving "hypercholesterolemia" lands on "familial hypercholesterolemia").
  • PICK the candidate that best matches what the user meant, then resolve THAT one with resolve_* —
    silently. Choose the most on-point term for their intent: for a lay phrase ("high cholesterol") prefer
    the closest common clinical or measurement term, not a rare subtype; don't pick a narrow familial/
    syndromic form when they mean the common condition, and don't pick a lab-measurement trait when they
    mean the disease (or vice-versa).
  • ASK the user ONLY when the candidates are genuinely ambiguous — several distinct, roughly-equally
    plausible entities with no clear best match, or the query is too vague to choose. Then show a short
    numbered list (name + one-line description + profile link) and let them pick.
When all three are resolved, STOP with a single friendly line that NAMES what you locked in (so the user
can correct you if a pick is off), e.g. "All set — evolocumab, PCSK9, and high LDL cholesterol. Ready to
dig into the claim whenever you are." Do NOT give a verdict here — pinning down the entities is Stage 1's
whole job, whether or not you had to ask anything.

STAGE 2 — red-team the claim. ONLY after the user tells you to go ahead:
  • Call build_report ONCE, passing the resolved target symbol + Ensembl id, the disease name + EFO id,
    the drug name, and the direction the drug acts on the target ('inhibit' = lowers/blocks/antagonist/
    degrader, 'activate' = raises/agonist). If you know the drug's mechanism, supply the direction; for a
    novel drug or a bare idea, ASK the user whether it raises or lowers the target before calling.
  • build_report returns a full report: flagged concerns, checks that passed, not-applicable checks, and
    an overall assessment (which already notes likely mis-fires). The report panel shows the details to
    the user — your job is to NARRATE it.
  • Write your take in warm, plain language a biology grad would follow: the main concern(s) and why,
    which flags are probably false alarms (the assessment tells you) and why, and your overall read
    (does the claim hold, look shaky, or look refuted). Educate, don't dump — no raw id/URL walls.

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


# Like _as_str_tool, but also drops the raw dict result into `sink` — so stream_events can push the
# report to the UI panel (a "report" SSE event) in addition to returning it to the model.
def _capturing_tool(fn, sink: list):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        sink.append(result)
        return json.dumps(result)
    return wrapper


# Run one chat turn, yielding plain-dict events as they happen (the web layer turns these into SSE):
#   {"type": "status", "tool": <tool name>}   -- each time Claude decides to call a tool
#   {"type": "report", "data": <report dict>} -- the full red-team report, for the UI panel
#   {"type": "reply",  "text": <final text>}  -- the assistant's final answer for this turn
#   {"type": "error",  "message": <str>}      -- if anything fails
def stream_events(messages: list[dict]):
    reports: list = []   # build_report drops its result here so we can push it to the UI
    turn_tools = ([beta_tool(_as_str_tool(fn)) for fn in tools.RESOLVERS]
                  + [beta_tool(_capturing_tool(tools.build_report, reports))])
    try:
        runner = _client.beta.messages.tool_runner(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM,
            tools=turn_tools,
            messages=messages,
            output_config={"effort": "medium"},  # snappier for chat; raise for the final demo
        )
        reply = ""
        # The runner yields one assistant message per round. A round that calls tools has tool_use blocks
        # (the runner executes them, THEN loops); the final round ends the turn with the answer text.
        for message in runner:
            for block in message.content:
                if block.type == "tool_use":
                    yield {"type": "status", "tool": block.name}
            while reports:                        # a build_report ran in the prior round -> push it
                yield {"type": "report", "data": reports.pop(0)}
            if message.stop_reason == "end_turn":
                reply = "".join(b.text for b in message.content if b.type == "text")
        while reports:                            # flush any report from the final round
            yield {"type": "report", "data": reports.pop(0)}
        yield {"type": "reply", "text": reply or "(no reply)"}
    except Exception as e:
        yield {"type": "error", "message": f"{type(e).__name__}: {e}"}
