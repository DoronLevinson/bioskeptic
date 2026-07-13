// ── theme toggle (light default; remembered) ──────────────────────────────
const root = document.documentElement;
const themeToggle = document.getElementById("themeToggle");
function applyThemeState() {
  const dark = root.dataset.theme === "dark";
  themeToggle.classList.toggle("on", dark);
  const lbl = document.getElementById("themeLabel");
  if (lbl) lbl.textContent = dark ? "Dark" : "Light";
}
applyThemeState();
themeToggle.addEventListener("click", () => {
  root.dataset.theme = root.dataset.theme === "dark" ? "" : "dark";
  try { localStorage.setItem("theme", root.dataset.theme); } catch (e) {}
  applyThemeState();
});

// ── brand = start a new conversation (a fresh reload; the old convo isn't saved) ──
document.getElementById("brandHome").addEventListener("click", () => location.reload());

// ── comparison mode toggle (demo, visual only for now) ────────────────────
const compareToggle = document.getElementById("compareToggle");
let compareMode = false;
compareToggle.addEventListener("click", () => {
  compareMode = !compareMode;
  compareToggle.classList.toggle("on", compareMode);
  // (a demo switch for now — wired up when we build the side-by-side comparison)
});

// ── red-team report panel ─────────────────────────────────────────────────
const reportPanel = document.getElementById("reportPanel");
const reportBody = document.getElementById("reportBody");
const reportClaim = document.getElementById("reportClaim");
const reportSummary = document.getElementById("reportSummary");
const reportToggle = document.getElementById("reportToggle");
const reportClose = document.getElementById("reportClose");
const reportRail = document.getElementById("reportRail");

// "open" = expanded to fill the left half; removing it collapses back to the thin rail (never disappears).
// Until the user drags to resize, opening sizes the report to half the space right of the sidebar.
let reportUserSized = false;
function halfWidth() {
  const sidebar = document.querySelector(".sidebar").offsetWidth;
  return Math.round((window.innerWidth - sidebar - 12) / 2);
}
function openReport() {
  if (!reportUserSized) document.documentElement.style.setProperty("--report-w", halfWidth() + "px");
  reportPanel.classList.add("open");
  reportToggle.classList.add("on");
}
function collapseReport() {
  reportPanel.classList.remove("open");
  reportToggle.classList.remove("on");
}
reportRail.addEventListener("click", openReport);
reportClose.addEventListener("click", collapseReport);
reportToggle.addEventListener("click", () => (reportPanel.classList.contains("open") ? collapseReport() : openReport()));

// drag handles: sidebar width, and the report/chat split (both stored as CSS vars)
function initResizer(el) {
  el.addEventListener("mousedown", (e) => {
    e.preventDefault();
    el.classList.add("dragging");
    document.body.style.userSelect = "none";
    const target = el.dataset.target;
    const move = (ev) => {
      const sidebar = document.querySelector(".sidebar").offsetWidth;
      if (target === "sidebar") {
        const w = Math.min(Math.max(ev.clientX, 160), 420);
        document.documentElement.style.setProperty("--sidebar-w", w + "px");
      } else {
        const w = Math.min(Math.max(ev.clientX - sidebar - 5, 300), window.innerWidth - sidebar - 380);
        document.documentElement.style.setProperty("--report-w", w + "px");
        reportUserSized = true;
      }
    };
    const up = () => {
      el.classList.remove("dragging");
      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", move);
      window.removeEventListener("mouseup", up);
    };
    window.addEventListener("mousemove", move);
    window.addEventListener("mouseup", up);
  });
}
initResizer(document.getElementById("sidebarResizer"));
initResizer(document.getElementById("reportResizer"));

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
// summary counts: red = flagged mechanisms, orange = agent-added concerns (literature/reasoning/etc.,
// grows as add_concern streams in), green = passed, grey = no data. Rendered as a 4-stat strip.
let reportCounts = { red: 0, orange: 0, green: 0, grey: 0 };
function renderSummary() {
  const stats = [
    ["red", reportCounts.red, "possible refuting mechanisms"],
    ["orange", reportCounts.orange, "concerns from literature & reasoning"],
    ["green", reportCounts.green, "refuting mechanisms passed"],
    ["grey", reportCounts.grey, "checks with no data"],
  ];
  reportSummary.innerHTML = stats.map(([cls, n, txt]) =>
    `<div class="sum-stat ${cls}"><span class="sum-num">${n}</span><span class="sum-txt">${esc(txt)}</span></div>`).join("");
}

// Base report: title + claim + summary + the deterministic mechanism panel. The "Concerns to weigh" and
// "Evidence pulled" sections start hidden and fill in live as add_concern / the dig tools stream events.
function renderReport(d) {
  const c = d.claim || {};
  const dir = c.direction ? `<span class="dir">${esc(c.direction)}s</span> ` : "";
  reportClaim.innerHTML = `<b>${esc(c.drug || "—")}</b> — ${dir}<b>${esc(c.target || "—")}</b> · ${esc(c.disease || "—")}`;
  reportCounts = { red: d.flagged.length, orange: 0, green: d.clean.length, grey: (d.not_applicable || []).length };
  renderSummary();
  let html = "";
  html += `<h4 class="report-sec" id="concernsSec" hidden>▲ Concerns to weigh</h4>`;
  html += `<div id="concernsList" class="card-grid"></div>`;
  html += `<h4 class="report-sec">⚑ Refuting mechanisms flagged (${d.flagged.length})</h4>`;
  html += `<div class="card-grid">${d.flagged.length ? d.flagged.map((m) => mechCard(m, true)).join("")
                                                      : `<div class="report-none">Nothing flagged.</div>`}</div>`;
  html += `<h4 class="report-sec">✓ Refuting mechanisms passed (${d.clean.length})</h4>`;
  html += `<div class="card-grid">${d.clean.map((m) => mechCard(m, false)).join("")}</div>`;
  if ((d.not_applicable || []).length) {
    html += `<h4 class="report-sec">— No data (${d.not_applicable.length})</h4>`;
    html += `<div class="na-chips">${d.not_applicable.map((m) => `<span class="na-chip">${esc(m.title)}</span>`).join("")}</div>`;
  }
  html += `<h4 class="report-sec" id="evidenceSec" hidden>🔎 Evidence the red-teamer pulled</h4>`;
  html += `<div id="evidenceList"></div>`;
  reportBody.innerHTML = html;
  reportToggle.hidden = false;          // reveal the sidebar Report toggle
  reportPanel.classList.add("shown");   // rail appears beside the sidebar (stays collapsed)
}

// ── live report growth: concerns (agent-curated, ranked) and evidence (dig tools) ─────────
const SEV_ORDER = { high: 0, medium: 1, low: 2 };
function concernCard(c) {
  const sev = SEV_ORDER[c.severity] != null ? c.severity : "medium";
  const fa = c.likely_false_alarm ? `<span class="concern-fa">likely false alarm</span>` : "";
  const org = c.origin ? `<span class="concern-origin">${esc(c.origin)}</span>` : "";
  const basis = c.basis ? `<span class="concern-basis">${esc(c.basis)}</span>` : "";
  const srcs = (c.sources || []).map((u) => urlChip(u)).join(" ");
  const meta = (org || basis || srcs) ? `<div class="concern-meta">${org}${basis}${srcs}</div>` : "";
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
  // count agent-added (non-mechanism) concerns toward the orange summary stat
  if (c.origin && c.origin !== "mechanism") { reportCounts.orange += 1; renderSummary(); }
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
  drug_targets: "Finding the drug's targets",
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

// ── demo suggestions: prefill the composer with example prompts ─────────────
const demoHint = document.getElementById("demoHint");
const demoPanel = document.getElementById("demoPanel");
const composerArea = document.getElementById("composerArea");
const DEMOS = [
  { group: "Get started", items: [
    { text: "Hello, can you introduce yourself?" },
    { text: "What is BioSkeptic?" },
  ]},
  { group: "Red-team a claim", items: [
    { text: "Red-team this: adalimumab inhibits TNF to treat rheumatoid arthritis", tag: "correct claim" },
    { text: "Red-team this: an activator of PCSK9 to treat Alzheimer's disease", tag: "false claim" },
    { text: "Red-team this: an activator of ZNF229 for high LDL cholesterol", tag: "false · obscure" },
  ]},
];
demoPanel.innerHTML = DEMOS.map((g, gi) =>
  `<div class="demo-group"><div class="demo-group-h">${esc(g.group)}</div>` +
  g.items.map((it, i) =>
    `<button type="button" class="demo-item" data-g="${gi}" data-i="${i}"><span>${esc(it.text)}</span>` +
    (it.tag ? `<span class="demo-tag">${esc(it.tag)}</span>` : "") + `</button>`
  ).join("") + `</div>`).join("");

demoHint.addEventListener("click", () => { demoPanel.hidden = !demoPanel.hidden; });
document.addEventListener("click", (e) => {            // click outside closes the panel
  if (!demoPanel.hidden && !composerArea.contains(e.target)) demoPanel.hidden = true;
});
demoPanel.querySelectorAll(".demo-item").forEach((btn) => {
  btn.addEventListener("click", () => {                // prefill the box, ready to send (not auto-sent)
    input.value = DEMOS[+btn.dataset.g].items[+btn.dataset.i].text;
    demoPanel.hidden = true;
    input.focus();
  });
});
function hideDemos() {                                  // once a report exists, retire the demos for good
  demoPanel.hidden = true;
  demoHint.style.display = "none";
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
          openReport();                        // open by default the moment the report is created
          sawReport = true;
          hideDemos();                         // a report exists now — retire the example prompts
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
