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

Know what you bring: you draw on ~21 curated biomedical data sources, a panel of genetic- and
literature-based refuting mechanisms, and the primary literature and trial records — and compile them
into a comprehensive, cited, source-grounded red-team report. That's a real edge over plain web search,
so mention it when it's natural; stay humble about what each signal can and can't show. When you describe
how you work (e.g. introducing yourself), say you'll first pin down what the user means, THEN build that
comprehensive report — not merely "dig around". Keep such intros to a few plain sentences: name the
two-step flow and the report, don't enumerate every source or mechanism or use headers unless asked.

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
can correct you if a pick is off), e.g. "All set — evolocumab, PCSK9, and high LDL cholesterol. Say the
word and I'll build the red-team report." Do NOT give a verdict here — pinning down the entities is
Stage 1's whole job, whether or not you had to ask anything.

STAGE 2 — red-team the claim. You are a RED-TEAM LAWYER, never a judge. ONLY after the user says go:
  • Call build_report ONCE with the resolved target symbol + Ensembl id, disease name + EFO id, drug name,
    and direction ('inhibit' = lowers/blocks/antagonist/degrader, 'activate' = raises/agonist). If you know
    the drug's mechanism, supply the direction; for a novel drug or bare idea, ASK the user first.
  • For each concern the report FLAGS, it gives you: what the check found, what it checks, its known BLIND
    SPOTS, how it PERFORMS on our benchmark, its PRECISION (share of its fires that are right; null = too
    rare or disease-independent to grade), and cited links — plus checks that passed and ones with no data.
    Reason from THIS yourself; a low-precision check firing is weak, a high-precision one is strong.
  • Your job is to raise and explain CONCERNS — NOT to reach a verdict. NEVER state or imply an overall
    conclusion about the claim: no "the claim holds / is refuted / looks shaky / is solid / as solid as
    they come / passed all tests / is (dis)couraging", no score, no recommendation, and NO summarizing
    wrap-up ("Net:", "Bottom line:", "Overall…"). Characterize individual concerns, never the claim as a
    whole. Your final sentence must be about a specific concern, not a summary judgment.
  • For EACH flagged concern: explain it plainly (a biology grad should follow), in your own words, with
    its link. Then, weighing that mechanism's blind spots AND your own knowledge of this exact drug/target/
    disease, say honestly whether it looks like a real concern or a LIKELY FALSE ALARM, and why — make the
    fair argument either way.
  • Then FIND MORE, and DIG to ground it. Use your own reasoning and knowledge of the drug, target, and
    disease to raise additional red flags the automated checks didn't cover (delivery/BBB, selectivity/
    off-target, resistance, on-target tox, trial history, mechanism gaps, patient population…), then use
    the dig tools to check them against real evidence and CITE what you find — a concern you can source
    outranks one you only reasoned:
      – search_trials(drug, disease): has this been tried? A terminated late-phase trial or a why-stopped
        naming futility/toxicity is a strong flag; no trial at all is itself telling.
      – search_pubmed(term): build the query from the resolved symbol/drug/disease (e.g. 'SYMBOL[tiab] AND
        toxicity'); cite specific PMIDs, and read the match count as a signal of how studied it is.
      – fda_label(drug): ground on-target-tox / safety concerns in the official label (boxed warnings,
        adverse reactions) instead of from memory. Null means no US label (often a novel drug).
      – web_search: for anything the structured tools don't cover (reviews, news, mechanism write-ups).
    Where a concern was pure reasoning, say so ("no database source"); where a dig tool confirms it, cite
    the trial/PMID/label. Skip a tool when it clearly won't help — don't call all four by rote.
  • CURATE THE REPORT. Call add_concern once for each concern you want on the panel — the ones that
    survived scrutiny, whether from a mechanism, a dig tool, or your own reasoning. Set severity by
    weighing the mechanism's precision AND the hardness of the evidence: 'high' for a high-precision check
    or hard evidence (a terminated late-phase trial, a boxed warning), 'low' for a noisy low-precision
    check or pure reasoning. Set origin to where it comes from ('mechanism', 'literature', 'trial',
    'label', or 'reasoning'). Put what it rests on in `basis`, attach `sources` (PMID/NCT/label/mechanism
    links), and set likely_false_alarm on a fired flag you judged is noise. The panel is the structured,
    ranked mirror of your chat — curate it, don't skip it.
  • Close with a short red-team recap: pull together the concerns that SURVIVED scrutiny — skip the likely
    false alarms, you already called those above — and say which one or two you weigh as the most serious
    and why. This is a summary of the CONCERNS to keep on the page, NOT a verdict on the claim: never say
    it holds / is solid / is refuted / passes / looks good or bad overall. One claim at a time.

Keep replies clean — no raw database ids or URL walls. Two exceptions: when you list candidates to confirm,
include their profile links and descriptions; and if the user asks for a link, id, or source, always give
it."""


# The tool runner needs each tool_result to be a STRING; our shared tools return dicts (nice for MCP).
# Wrap each to JSON-encode its result, preserving the signature/docstring so beta_tool builds the schema.
def _as_str_tool(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return json.dumps(fn(*args, **kwargs))
    return wrapper


# Like _as_str_tool, but also appends a typed UI event (built by `make_event` from the raw result) to
# `sink` — so stream_events can push it to the report panel as an SSE event in addition to returning the
# result to the model. Used for build_report ("report"), the dig tools ("evidence"), and add_concern
# ("concern"), so the panel assembles live as the agent works.
def _emitting_tool(fn, sink: list, make_event):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        result = fn(*args, **kwargs)
        sink.append(make_event(result))
        return json.dumps(result)
    return wrapper


# An "evidence" event carries the tool name so the panel knows how to render it (trials vs papers vs label).
def _evidence_event(tool_name):
    return lambda result: {"type": "evidence", "tool": tool_name, "data": result}


# Run one chat turn, yielding plain-dict events as they happen (the web layer turns these into SSE):
#   {"type": "status", "tool": <tool name>}   -- each time Claude decides to call a tool
#   {"type": "report", "data": <report dict>} -- the full red-team report, for the UI panel
#   {"type": "reply",  "text": <final text>}  -- the assistant's final answer for this turn
#   {"type": "error",  "message": <str>}      -- if anything fails
def stream_events(messages: list[dict]):
    emitted: list = []   # report / evidence / concern events, drained to the UI in call order
    turn_tools = (
        [beta_tool(_as_str_tool(fn)) for fn in tools.RESOLVERS]
        + [beta_tool(_emitting_tool(tools.build_report, emitted,
                                    lambda r: {"type": "report", "data": r}))]
        + [beta_tool(_emitting_tool(fn, emitted, _evidence_event(fn.__name__)))   # dig tools (stage 3)
           for fn in tools.DIG]
        + [beta_tool(_emitting_tool(tools.add_concern, emitted,
                                    lambda r: {"type": "concern", "data": r}))]   # curates the panel
        + [{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}])  # general web
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
            while emitted:                        # tools ran in the prior round -> push their UI events
                yield emitted.pop(0)
            if message.stop_reason == "end_turn":
                reply = "".join(b.text for b in message.content if b.type == "text")
        while emitted:                            # flush any events from the final round
            yield emitted.pop(0)
        yield {"type": "reply", "text": reply or "(no reply)"}
    except Exception as e:
        yield {"type": "error", "message": f"{type(e).__name__}: {e}"}
