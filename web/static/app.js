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
        } else if (event.type === "reply") {
          bubble.className = "msg bot";
          bubble.innerHTML = renderMarkdown(event.text);
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
