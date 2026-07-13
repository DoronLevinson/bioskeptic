// ── theme toggle (light default; remembered) ──────────────────────────────
const root = document.documentElement;
const themeToggle = document.getElementById("themeToggle");
function applyThemeIcon() {
  themeToggle.textContent = root.dataset.theme === "dark" ? "☀" : "☾";
}
applyThemeIcon();
themeToggle.addEventListener("click", () => {
  root.dataset.theme = root.dataset.theme === "dark" ? "" : "dark";
  try { localStorage.setItem("theme", root.dataset.theme); } catch (e) {}
  applyThemeIcon();
});

// ── comparison mode toggle (visual only for now) ──────────────────────────
const compareToggle = document.getElementById("compareToggle");
let compareMode = false;
compareToggle.addEventListener("click", () => {
  compareMode = !compareMode;
  compareToggle.classList.toggle("on", compareMode);
  // (does nothing else yet — wired up when we build the side-by-side panel)
});

// ── red-team report panel ─────────────────────────────────────────────────
const reportPanel = document.getElementById("reportPanel");
const reportBody = document.getElementById("reportBody");
const reportClaim = document.getElementById("reportClaim");
const reportToggle = document.getElementById("reportToggle");
const reportClose = document.getElementById("reportClose");
const reportRail = document.getElementById("reportRail");
// "open" = expanded to the right; removing it collapses back to the thin rail (never disappears)
const openReport = () => reportPanel.classList.add("open");
const collapseReport = () => reportPanel.classList.remove("open");
reportRail.addEventListener("click", openReport);
reportClose.addEventListener("click", collapseReport);
reportToggle.addEventListener("click", () => reportPanel.classList.toggle("open"));

function srcChip(s) {
  return `<a class="src-chip" href="${s.url}" target="_blank" rel="noopener">${esc(s.label)} ↗</a>`;
}
// short host name for a bare url (concern / evidence citations)
function urlChip(u, label) {
  let name = label;
  if (!name) { try { name = new URL(u).hostname.replace(/^www\./, "").split(".")[0]; } catch (e) { name = "link"; } }
  return `<a class="src-chip" href="${u}" target="_blank" rel="noopener">${esc(name)} ↗</a>`;
}
function precTag(m) {
  return (m.precision != null)
    ? `<span class="mech-prec" title="benchmark precision — share of its fires that are right">prec ${m.precision.toFixed(2)}</span>`
    : "";
}
function mechCard(m, fired) {
  const srcs = (m.sources || []).map(srcChip).join(" ");
  return `<div class="mech-card ${fired ? "fired" : "clean"}">
    <div class="mech-title">${esc(m.title)}<span class="mech-tag">${fired ? "flagged" : "passed"}</span>${precTag(m)}</div>
    <div class="mech-what">${esc(m.what_it_checks)}</div>
    <div class="mech-finding">${esc(m.finding)}</div>
    ${srcs ? `<div class="mech-src">${srcs}</div>` : ""}
  </div>`;
}
// Base report: the claim + the deterministic mechanism panel. The "Concerns to weigh" and "Evidence
// pulled" sections start hidden and fill in live as add_concern / the dig tools stream events.
function renderReport(d) {
  const c = d.claim || {};
  const dir = c.direction ? `<span class="dir">${esc(c.direction)}s</span> ` : "";
  reportClaim.innerHTML = `<b>${esc(c.drug || "—")}</b> — ${dir}<b>${esc(c.target || "—")}</b> · ${esc(c.disease || "—")}`;
  let html = "";
  html += `<h4 class="report-sec" id="concernsSec" hidden>▲ Concerns to weigh</h4>`;
  html += `<div id="concernsList"></div>`;
  html += `<h4 class="report-sec">⚑ Concerns flagged (${d.flagged.length})</h4>`;
  html += d.flagged.length ? d.flagged.map((m) => mechCard(m, true)).join("")
                           : `<div class="report-none">Nothing flagged.</div>`;
  html += `<h4 class="report-sec">✓ Checks that passed (${d.clean.length})</h4>`;
  html += d.clean.map((m) => mechCard(m, false)).join("");
  if ((d.not_applicable || []).length) {
    html += `<h4 class="report-sec">— Not applicable (${d.not_applicable.length})</h4>`;
    html += `<div class="na-chips">${d.not_applicable.map((m) => `<span class="na-chip">${esc(m.title)}</span>`).join("")}</div>`;
  }
  html += `<h4 class="report-sec" id="evidenceSec" hidden>🔎 Evidence the red-teamer pulled</h4>`;
  html += `<div id="evidenceList"></div>`;
  reportBody.innerHTML = html;
  reportToggle.hidden = false;          // reveal the toolbar toggle
  reportPanel.classList.add("shown");   // rail appears beside the sidebar (stays collapsed)
}

// ── live report growth: concerns (agent-curated, ranked) and evidence (dig tools) ─────────
const SEV_ORDER = { high: 0, medium: 1, low: 2 };
function concernCard(c) {
  const sev = SEV_ORDER[c.severity] != null ? c.severity : "medium";
  const fa = c.likely_false_alarm ? `<span class="concern-fa">likely false alarm</span>` : "";
  const basis = c.basis ? `<span class="concern-basis">${esc(c.basis)}</span>` : "";
  const srcs = (c.sources || []).map((u) => urlChip(u)).join(" ");
  const meta = (basis || srcs) ? `<div class="concern-meta">${basis}${srcs}</div>` : "";
  return `<div class="concern-card sev-${sev}" data-sev="${sev}">
    <div class="concern-title"><span class="sev-dot"></span>${esc(c.title)}${fa}</div>
    <div class="concern-explain">${esc(c.explanation)}</div>${meta}
  </div>`;
}
function addConcern(c) {
  const list = document.getElementById("concernsList");
  if (!list) return;
  const wrap = document.createElement("div");
  wrap.innerHTML = concernCard(c);
  list.appendChild(wrap.firstElementChild);
  // keep the list sorted high → medium → low as cards stream in
  [...list.children]
    .sort((a, b) => (SEV_ORDER[a.dataset.sev] ?? 1) - (SEV_ORDER[b.dataset.sev] ?? 1))
    .forEach((n) => list.appendChild(n));
  const sec = document.getElementById("concernsSec"); if (sec) sec.hidden = false;
}
function evidenceCard(tool, d) {
  if (tool === "search_trials") {
    const chips = (d.trials || []).map((t) => {
      const stopped = /TERMINATED|WITHDRAWN|SUSPENDED/.test(t.status || "");
      const why = t.why_stopped ? ` — ${esc(t.why_stopped)}` : "";
      return `<a class="trial-chip ${stopped ? "stopped" : ""}" href="${t.url}" target="_blank" rel="noopener">${esc(t.nct)} · ${esc(t.phase)} · ${esc(t.status)}${why} ↗</a>`;
    }).join("");
    return `<div class="ev-card"><div class="ev-h">🧪 Trials <span class="ev-count">${d.total_count}</span></div>
      <div class="ev-chips">${chips || `<span class="report-none">no matching trials</span>`}</div></div>`;
  }
  if (tool === "search_pubmed") {
    const chips = (d.papers || []).map((p) =>
      `<a class="src-chip" href="${p.url}" target="_blank" rel="noopener">${esc(p.first_author || ("PMID " + p.pmid))}${p.year ? " (" + esc(p.year) + ")" : ""} ↗</a>`).join(" ");
    return `<div class="ev-card"><div class="ev-h">📄 Literature <span class="ev-count">${d.total_count}</span></div>
      <div class="ev-sub">${esc(d.query || "")}</div><div class="ev-chips">${chips}</div></div>`;
  }
  if (tool === "fda_label") {
    if (!d) return `<div class="ev-card"><div class="ev-h">💊 FDA label</div><div class="report-none">no US label (often a novel drug)</div></div>`;
    const secs = Object.entries(d.sections || {}).map(([k, v]) =>
      `<div class="fda-sec"><b>${esc(k)}</b> ${esc(v.slice(0, 260))}${v.length > 260 ? "…" : ""}</div>`).join("");
    return `<div class="ev-card"><div class="ev-h">💊 FDA label ${urlChip(d.url, d.brand || "DailyMed")}</div>${secs}</div>`;
  }
  return "";
}
function addEvidence(tool, d) {
  const html = evidenceCard(tool, d);
  if (!html) return;
  const list = document.getElementById("evidenceList");
  if (!list) return;
  const wrap = document.createElement("div");
  wrap.innerHTML = html;
  list.appendChild(wrap.firstElementChild);
  const sec = document.getElementById("evidenceSec"); if (sec) sec.hidden = false;
}

// ── sidebar page switching ────────────────────────────────────────────────
document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-item").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const page = btn.dataset.page;
    document.querySelectorAll(".page").forEach((s) => { s.hidden = s.id !== "page-" + page; });
  });
});

// ── chat ──────────────────────────────────────────────────────────────────
const chat = document.getElementById("page-home");
const log = document.getElementById("log");
const form = document.getElementById("form");
const input = document.getElementById("input");
const send = document.getElementById("send");
const messages = [];   // full history, sent to the stateless server each turn

// friendly label for each tool, shown in the live status line
const LABELS = {
  suggest_drugs: "Scanning drug candidates",
  resolve_drug: "Resolving the drug",
  suggest_targets: "Scanning target candidates",
  resolve_target: "Resolving the target",
  suggest_diseases: "Scanning disease candidates",
  resolve_disease: "Resolving the disease",
  build_report: "Running the red-team panel",
  search_trials: "Searching clinical trials",
  search_pubmed: "Searching PubMed",
  fda_label: "Reading the FDA label",
  add_concern: "Noting a concern",
  web_search: "Searching the web",
};

const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// minimal markdown -> HTML: headings, bold/italic/code, links, unordered/ordered lists
function renderMarkdown(md) {
  const inline = (t) => t
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    // bare URL (not already inside a link's href) -> a compact clickable "(link)"
    .replace(/(?<!["(=])\bhttps?:\/\/[^\s<]+/g, (u) => `<a href="${u}" target="_blank" rel="noopener">(link)</a>`);
  let html = "", list = null;
  const closeList = () => { if (list) { html += `</${list}>`; list = null; } };
  for (const raw of esc(md).split("\n")) {
    const line = raw.replace(/\s+$/, "");
    let m;
    if ((m = line.match(/^(#{1,6})\s+(.*)/))) {
      closeList();
      html += `<h${Math.min(m[1].length + 1, 4)}>${inline(m[2])}</h${Math.min(m[1].length + 1, 4)}>`;
    } else if ((m = line.match(/^\s*[-*]\s+(.*)/))) {
      if (list !== "ul") { closeList(); html += "<ul>"; list = "ul"; }
      html += `<li>${inline(m[1])}</li>`;
    } else if ((m = line.match(/^\s*\d+\.\s+(.*)/))) {
      if (list !== "ol") { closeList(); html += "<ol>"; list = "ol"; }
      html += `<li>${inline(m[1])}</li>`;
    } else if (line.trim() === "") {
      // keep any open list open across blank lines, so "1. …\n\n2. …" stays one <ol> (correct numbering)
    } else {
      closeList();
      html += `<p>${inline(line)}</p>`;
    }
  }
  closeList();
  return html;
}

function scrollDown() { log.scrollTop = log.scrollHeight; log.parentElement.scrollTop = log.parentElement.scrollHeight; }

function addUser(text) {
  const div = document.createElement("div");
  div.className = "msg user";
  div.textContent = text;
  log.appendChild(div);
  scrollDown();
}
function newBotBubble() {
  const div = document.createElement("div");
  div.className = "msg bot status";
  div.innerHTML = `<span class="pulse">✳</span>Thinking…`;
  log.appendChild(div);
  scrollDown();
  return div;
}
function showStatus(bubble, tool) {
  const label = LABELS[tool] || tool.replace(/_/g, " ");
  bubble.className = "msg bot status";
  bubble.innerHTML = `<span class="pulse">✳</span>${esc(label)}…`;
  scrollDown();
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  send.disabled = true;

  // first message: flip from the centered empty state to the conversation layout
  chat.classList.remove("empty");
  chat.classList.add("active");

  addUser(text);
  messages.push({ role: "user", content: text });
  const bubble = newBotBubble();
  let sawReport = false;   // did a report arrive this turn? (adds an "open report" link to the reply)

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages }),
    });
    // read the SSE stream: events separated by a blank line, each starts with "data:"
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const chunks = buffer.split("\n\n");
      buffer = chunks.pop();   // last piece may be incomplete; keep it for the next read
      for (const chunk of chunks) {
        const line = chunk.trim();
        if (!line.startsWith("data:")) continue;
        const event = JSON.parse(line.slice(5).trim());
        if (event.type === "status") {
          showStatus(bubble, event.tool);
        } else if (event.type === "report") {
          renderReport(event.data);
          sawReport = true;
        } else if (event.type === "concern") {
          addConcern(event.data);
        } else if (event.type === "evidence") {
          addEvidence(event.tool, event.data);
        } else if (event.type === "reply") {
          bubble.className = "msg bot";
          bubble.innerHTML = renderMarkdown(event.text);
          if (sawReport) {                       // add a link in the chat that opens the report
            const link = document.createElement("button");
            link.className = "open-report-link";
            link.textContent = "⚑ Open the full red-team report →";
            link.addEventListener("click", openReport);
            bubble.appendChild(link);
          }
          messages.push({ role: "assistant", content: event.text });
        } else if (event.type === "error") {
          bubble.className = "msg bot";
          bubble.textContent = "⚠️ " + event.message;
        }
      }
    }
  } catch (err) {
    bubble.className = "msg bot";
    bubble.textContent = "Error: " + err;
  } finally {
    send.disabled = false;
    input.focus();
    scrollDown();
  }
});
