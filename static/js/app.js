// ---------------------------------------------------------------------------
// Icons (inline SVG strings, reused across the action row / theme toggle)
// ---------------------------------------------------------------------------
const ICON_COPY = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const ICON_CHECK = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const ICON_REGEN = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6M1 20v-6h6" stroke-linecap="round" stroke-linejoin="round"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const ICON_THUMB_UP = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M7 22V11M2 13v7a2 2 0 0 0 2 2h13.4a2 2 0 0 0 2-1.7l1.4-9A2 2 0 0 0 19 9h-5.6l1-4.7A1.5 1.5 0 0 0 13 2.5L7 11" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const ICON_THUMB_DOWN = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 2v11m5 2v-7a2 2 0 0 0-2-2H6.6a2 2 0 0 0-2 1.7l-1.4 9A2 2 0 0 0 5 19h5.6l-1 4.7a1.5 1.5 0 0 0 2.4 1.5L17 13" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const ICON_TRASH = `<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16M9 7V4h6v3m-8 0 1 13h10l1-13" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const ICON_EDIT = `<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const ICON_DOWNLOAD = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v13m0 0 5-5m-5 5-5-5M4 20h16" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const ICON_ARCHIVE = `<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 8v13H3V8" stroke-linecap="round" stroke-linejoin="round"/><path d="M1 3h22v5H1z" stroke-linecap="round" stroke-linejoin="round"/><path d="M10 12h4" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const ICON_RESTORE = `<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 8v13H3V8" stroke-linecap="round" stroke-linejoin="round"/><path d="M1 3h22v5H1z" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 12v6m0-6-2.5 2.5M12 12l2.5 2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const ICON_FOLDER_CLOSED = `<svg viewBox="0 0 24 24" width="15" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1Z" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const ICON_FOLDER_OPEN = `<svg viewBox="0 0 24 24" width="15" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v1H6l-2.5 9L2 18V6Z" stroke-linecap="round" stroke-linejoin="round"/><path d="M3.5 18 6 9h15.5l-2.5 8.5a1 1 0 0 1-1 .7H4.4a1 1 0 0 1-.9-1.2Z" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const SEND_ICON = `<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
  <path d="M4 12h16M14 6l6 6-6 6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
const STOP_ICON = `<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>`;

function uid(prefix) {
  return `${prefix}-${Math.floor(Math.random() * 1e9)}`;
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

// ---------------------------------------------------------------------------
// Greeting-only messages ("hi", "good morning", ...) get an instant local
// reply — no reason to spend a Snowflake call/tokens on small talk.
// ---------------------------------------------------------------------------
const GREETING_ONLY_PATTERN = /^(hi+|hello+|hey+a?|yo+|howdy|greetings|sup|what'?s up|good\s?(morning|afternoon|evening|day)|hola|how('?s| is| are) (it going|things|you( doing)?))[\s!.?]*$/i;

function isGreetingOnly(text) {
  return GREETING_ONLY_PATTERN.test(text.trim());
}

function localGreetingReply() {
  const hour = new Date().getHours();
  const part = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
  const name = document.body.dataset.chatbotName || "Supply Chain KG";
  return `Good ${part}! I'm ${name} — ask me anything about suppliers, parts, plants, shipments or inventory, and I'll pull the answer straight from the data.`;
}

// ---------------------------------------------------------------------------
// Theme (dark/light)
// ---------------------------------------------------------------------------
const THEME_KEY = "eno-theme";
const themeToggle = document.getElementById("theme-toggle");

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  if (themeToggle) {
    const label = theme === "dark" ? "Switch to light mode" : "Switch to dark mode";
    themeToggle.setAttribute("aria-label", label);
    themeToggle.setAttribute("title", label);
  }
}

(function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  const theme = saved || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  applyTheme(theme);
})();

themeToggle?.addEventListener("click", () => {
  const current = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
  const next = current === "dark" ? "light" : "dark";
  applyTheme(next);
  localStorage.setItem(THEME_KEY, next);
});

// ---------------------------------------------------------------------------
// Sidebar collapse
// ---------------------------------------------------------------------------
const SIDEBAR_KEY = "eno-sidebar-collapsed";
const sidebarToggle = document.getElementById("sidebar-toggle");

function applySidebarCollapsed(collapsed) {
  document.body.classList.toggle("sidebar-collapsed", collapsed);
  if (sidebarToggle) {
    const label = collapsed ? "Expand sidebar" : "Collapse sidebar";
    sidebarToggle.setAttribute("aria-label", label);
    sidebarToggle.setAttribute("title", label);
  }
}

(function initSidebar() {
  applySidebarCollapsed(localStorage.getItem(SIDEBAR_KEY) === "1");
})();

function toggleSidebar() {
  const collapsed = !document.body.classList.contains("sidebar-collapsed");
  applySidebarCollapsed(collapsed);
  localStorage.setItem(SIDEBAR_KEY, collapsed ? "1" : "0");
}
sidebarToggle?.addEventListener("click", toggleSidebar);

// ---------------------------------------------------------------------------
// Sidebar resize (drag the right edge) — defaults to 550px, persisted
// across reloads like the collapse state.
// ---------------------------------------------------------------------------
const SIDEBAR_WIDTH_KEY = "eno-sidebar-width";
const DEFAULT_SIDEBAR_WIDTH = 550;
const MIN_SIDEBAR_WIDTH = 220;
const MAX_SIDEBAR_WIDTH = 560;
const sidebarEl = document.getElementById("sidebar");
const sidebarResizeHandle = document.getElementById("sidebar-resize-handle");

function applySidebarWidth(px) {
  document.documentElement.style.setProperty("--sidebar-width", `${px}px`);
}

(function initSidebarWidth() {
  const stored = parseInt(localStorage.getItem(SIDEBAR_WIDTH_KEY), 10);
  applySidebarWidth(Number.isFinite(stored) ? stored : DEFAULT_SIDEBAR_WIDTH);
})();

sidebarResizeHandle?.addEventListener("mousedown", (e) => {
  e.preventDefault();
  sidebarEl.classList.add("resizing");
  const startX = e.clientX;
  const startWidth = sidebarEl.getBoundingClientRect().width;

  function onMouseMove(ev) {
    const next = Math.min(MAX_SIDEBAR_WIDTH, Math.max(MIN_SIDEBAR_WIDTH, startWidth + (ev.clientX - startX)));
    applySidebarWidth(next);
  }
  function onMouseUp() {
    sidebarEl.classList.remove("resizing");
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
    localStorage.setItem(SIDEBAR_WIDTH_KEY, Math.round(sidebarEl.getBoundingClientRect().width));
  }
  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", onMouseUp);
});

// ---------------------------------------------------------------------------
// Greeting
// ---------------------------------------------------------------------------
(function renderGreeting() {
  const el = document.getElementById("greeting-text");
  if (!el) return;
  const hour = new Date().getHours();
  const part = hour < 12 ? "morning" : hour < 18 ? "afternoon" : "evening";
  const name = el.dataset.fullName || "";
  el.innerHTML = `Good ${part}, <span class="greeting-name">${escapeHtml(name)}</span>`;
})();

// ---------------------------------------------------------------------------
// Markdown / result table / chart helpers
// ---------------------------------------------------------------------------
// LLM-generated markdown is often slightly malformed in ways that trip up a
// strict parser: 3+ blank lines between paragraphs, or a table/list glued
// directly to the previous sentence with no blank line before it (which
// makes marked leave the raw "|" / "-" characters as plain text instead of
// rendering a table or list).
function normalizeMarkdown(text) {
  let out = String(text);
  // A markdown table's rows must be contiguous — a blank line anywhere
  // inside one (which the model sometimes inserts between rows) splits it
  // into disconnected fragments instead of one table. Collapse those first.
  out = out.replace(/(\|[^\n]*\|)[ \t]*\n(?:[ \t]*\n)+(?=[ \t]*\|)/g, "$1\n");
  out = out.replace(/\n{3,}/g, "\n\n");
  // Only glue-fix a table/list that follows plain prose — "[^\n|]" excludes
  // lines that themselves end in "|", so two already-contiguous table rows
  // are never pried back apart with a re-inserted blank line.
  out = out.replace(/([^\n|])\n(\|.*\|)/g, "$1\n\n$2");
  out = out.replace(/([^\n])\n((?:[-*+]|\d+[.)])\s)/g, "$1\n\n$2");
  // The model writes "~" for "approximately" (e.g. "~0.15"), not strikethrough —
  // but marked's GFM tokenizer treats any two stray tildes as a ~~del~~ pair,
  // so escape every literal tilde to keep it displaying as plain text.
  out = out.replace(/~/g, "\\~");
  return out.trim();
}

function renderMarkdown(text) {
  const html = marked.parse(normalizeMarkdown(text), { gfm: true, breaks: true });
  return DOMPurify.sanitize(html);
}

function isNumericColumn(rows, colIndex) {
  return rows.some((r) => typeof r[colIndex] === "number") &&
    rows.every((r) => r[colIndex] === null || typeof r[colIndex] === "number");
}

// jspdf-autotable columnStyles for a table body — right-aligns any column
// that's entirely numeric, matching the on-screen ".num" right-alignment
// (th.num/td.num in style.css). Works on both raw numeric cells (SQL result
// rows) and the plain-string cells parsed out of a markdown table, since a
// numeric-looking string ("916.0") coerces cleanly with Number().
function pdfNumericColumnStyles(rows) {
  if (!rows || !rows.length) return {};
  const styles = {};
  const colCount = rows[0].length;
  for (let c = 0; c < colCount; c++) {
    const vals = rows.map((r) => r[c]);
    const isBlank = (v) => v === null || v === undefined || v === "";
    const isNumeric = vals.some((v) => !isBlank(v) && !isNaN(Number(v))) &&
      vals.every((v) => isBlank(v) || !isNaN(Number(v)));
    if (isNumeric) styles[c] = { halign: "right" };
  }
  return styles;
}

function formatCell(v) {
  if (v === null) return "";
  if (typeof v === "number") {
    const opts = Number.isInteger(v)
      ? { maximumFractionDigits: 0 }
      : { minimumFractionDigits: 2, maximumFractionDigits: 2 };
    return v.toLocaleString(undefined, opts);
  }
  return escapeHtml(v);
}

function renderResultTable(columns, rows) {
  if (!columns || !rows || !rows.length) return "";
  const numericCols = columns.map((_, i) => isNumericColumn(rows, i));
  const head = columns.map((c, i) =>
    `<th class="${numericCols[i] ? "num" : ""}">${escapeHtml(c)}</th>`).join("");
  const body = rows.map((r) =>
    `<tr>${r.map((v, i) => `<td class="${numericCols[i] ? "num" : ""}">${formatCell(v)}</td>`).join("")}</tr>`
  ).join("");
  return `<div class="table-wrap chat-table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

// unitScale tells us the agent's data is already pre-scaled (e.g. field
// "ENO_VALUE_BILLIONS" holding 4.87, not 4870000000) — in that case we must
// only append the right suffix, not divide again.
function formatUsdCompact(v, unitScale) {
  const n = Number(v) || 0;
  const sign = n < 0 ? "-" : "";
  const abs = Math.abs(n);
  if (unitScale === "billions") return `${sign}$${abs.toFixed(2)}B`;
  if (unitScale === "millions") return `${sign}$${abs.toFixed(2)}M`;
  if (abs >= 1e9) return `${sign}$${(abs / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(1)}K`;
  return `${sign}$${abs.toFixed(0)}`;
}

const CHART_PALETTE = ["#00aeef", "#f5a623", "#7c5cbf", "#2ecc71", "#e74c3c"];

// Renders the chart the agent itself decided the answer needed (translated
// server-side from its Vega-Lite spec) — preferred over the generic
// client-side column-guessing heuristic whenever the agent supplies one.
function renderAgentChart(canvas, chart) {
  const isBar = chart.type === "bar";
  new Chart(canvas, {
    type: chart.type === "line" ? "line" : "bar",
    data: {
      labels: chart.labels.map(String),
      datasets: chart.datasets.map((ds, i) => ({
        label: ds.label,
        data: ds.data.map((v) => Number(v) || 0),
        backgroundColor: isBar ? CHART_PALETTE[i % CHART_PALETTE.length] : "transparent",
        borderColor: CHART_PALETTE[i % CHART_PALETTE.length],
        borderRadius: isBar ? 4 : undefined,
        tension: 0.25,
        pointRadius: chart.type === "line" ? 2 : undefined,
      })),
    },
    options: {
      plugins: {
        legend: { display: chart.datasets.length > 1 },
        tooltip: chart.isCurrency ? {
          callbacks: { label: (ctx) => `${ctx.dataset.label}: ${formatUsdCompact(ctx.parsed.y, chart.unitScale)}` },
        } : undefined,
      },
      scales: {
        y: {
          beginAtZero: !chart.isCurrency,
          title: chart.yTitle ? { display: true, text: chart.yTitle } : undefined,
          ticks: chart.isCurrency ? { callback: (v) => formatUsdCompact(v, chart.unitScale) } : undefined,
        },
        x: {
          title: chart.xTitle ? { display: true, text: chart.xTitle } : undefined,
        },
      },
      maintainAspectRatio: false,
    },
  });
}

// ---------------------------------------------------------------------------
// Chat DOM references
// ---------------------------------------------------------------------------
const chatPanel = document.getElementById("chat-panel");
const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const chatSend = document.getElementById("chat-send");
const conciseToggle = document.getElementById("concise-toggle");
const newChatBtn = document.getElementById("new-chat-btn");
const historySearch = document.getElementById("history-search");
const followupSuggestions = document.getElementById("followup-suggestions");
const USER_INITIALS = document.body.dataset.userInitials || "U";

// Repeated auto-scroll during token streaming should only "stick" the view
// to the bottom while the user is already there — if they've scrolled up
// mid-stream to read something earlier, further deltas must not yank them
// back down. One-off scrolls (sending a question, opening the planning
// card, toggling a section) still jump unconditionally — those are actions
// the user themselves just took, so landing on the new content is expected.
function isNearChatBottom(threshold = 80) {
  return chatWindow.scrollHeight - chatWindow.scrollTop - chatWindow.clientHeight < threshold;
}

// Whether the view should keep following new content. Cleared as soon as the
// reader scrolls up — deliberately on a tighter threshold than isNearChatBottom's
// default, so a small scroll up during streaming is respected rather than
// snapped back by the next painted word — and set again when they return to the
// bottom or press Jump to latest.
let stickToBottomEnabled = true;

function scrollChatToBottom() {
  chatWindow.scrollTop = chatWindow.scrollHeight;
  stickToBottomEnabled = true;
  updateJumpLatestButton();
}

function stickToBottom() {
  if (stickToBottomEnabled) chatWindow.scrollTop = chatWindow.scrollHeight;
}

const jumpLatestBtn = document.getElementById("jump-latest-btn");

function updateJumpLatestButton() {
  if (!jumpLatestBtn) return;
  const scrollable = chatWindow.scrollHeight - chatWindow.clientHeight > 40;
  jumpLatestBtn.hidden = !(scrollable && !isNearChatBottom(48));
}

// The scroll handler may only ever RE-ENABLE following. It must not disable
// it: as an answer grows, scrollHeight jumps ahead of scrollTop, which fires a
// scroll event whose offset looks like "the reader scrolled up" when nothing
// of the sort happened. Disabling is therefore driven solely by real input
// gestures (wheel up, touch drag, Page Up / Up arrow) below.
chatWindow.addEventListener("scroll", () => {
  if (isNearChatBottom(48)) stickToBottomEnabled = true;
  updateJumpLatestButton();
});

// Wheel or trackpad upwards: stop following so the reader can look back.
chatWindow.addEventListener("wheel", (e) => {
  if (e.deltaY < 0) {
    stickToBottomEnabled = false;
    updateJumpLatestButton();
  }
}, { passive: true });

// Touch drag: a downward finger movement scrolls the content up.
let touchStartY = null;
chatWindow.addEventListener("touchstart", (e) => {
  touchStartY = e.touches[0]?.clientY ?? null;
}, { passive: true });
chatWindow.addEventListener("touchmove", (e) => {
  const y = e.touches[0]?.clientY;
  if (touchStartY !== null && y !== undefined && y - touchStartY > 8) {
    stickToBottomEnabled = false;
    updateJumpLatestButton();
  }
}, { passive: true });

// Reading back with the keyboard must stop the view following new output,
// exactly as scrolling up with the wheel does. A keypress is a clearer
// signal of intent than the resulting scroll offset, so it is handled
// directly rather than waiting for the scroll event to cross a threshold.
const SCROLL_UP_KEYS = new Set(["PageUp", "ArrowUp", "Home"]);
const SCROLL_DOWN_KEYS = new Set(["PageDown", "End"]);

function isTypingTarget(el) {
  if (!el) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "TEXTAREA" || el.isContentEditable;
}

document.addEventListener("keydown", (e) => {
  // Never hijack keys aimed at the question box or any other field.
  if (isTypingTarget(e.target)) return;
  if (SCROLL_UP_KEYS.has(e.key)) {
    stickToBottomEnabled = false;
    updateJumpLatestButton();
  } else if (SCROLL_DOWN_KEYS.has(e.key)) {
    // Jumping down is a request to catch up: resume following.
    stickToBottomEnabled = true;
    // Two-frame reveal rather than a direct scrollTop write: an expanded
    // table/graph may still be laying out, so the settled height is only
    // known a frame later.
    if (e.key === "End") revealAnswerEnd();
    updateJumpLatestButton();
  }
});

// Once the whole response (text plus table/chart/dropdowns/usage) is in the
// DOM, show its end. Two frames: the first lets the browser lay the new
// blocks out, the second scrolls against the settled height. Honours
// stickToBottomEnabled, so a reader who paged up stays where they were.
function revealAnswerEnd() {
  // The end of an answer settles late and for several unrelated reasons: a
  // chart canvas mounts, a Cytoscape graph lays out, fonts reflow, and on the
  // first question of a session the landing block collapses. Those change the
  // window's scrollHeight without necessarily resizing any one element, so
  // watch the height itself for a short window and follow it whenever it
  // moves. Every step honours stickToBottomEnabled, so a reader who pressed
  // Page Up is never pulled back down.
  const step = () => { stickToBottom(); updateJumpLatestButton(); };
  step();
  const deadline = performance.now() + 2500;
  let lastH = chatWindow.scrollHeight;
  cancelAnimationFrame(revealAnswerEnd._raf);
  (function follow(now) {
    const h = chatWindow.scrollHeight;
    if (h !== lastH) { lastH = h; step(); }
    if (now < deadline) revealAnswerEnd._raf = requestAnimationFrame(follow);
  })(performance.now());
}

jumpLatestBtn?.addEventListener("click", scrollChatToBottom);

// Snowflake's own agent stream doesn't flush one token at a time — it lands
// in bursts of a dozen-plus words with a few hundred ms of silence between
// them (confirmed by timestamping the raw SSE frames), so painting text_delta
// events straight to the DOM looks like chunks popping in, not streaming.
// This decouples "text has arrived" from "text is shown": every push() adds
// to a raw buffer, which gets re-tokenized into words, and a steady timer
// reveals one more word at a time regardless of how bursty the arrivals are.
// finish() hands over the authoritative final answer (in case it differs
// slightly from the concatenated deltas) and paints it in full immediately —
// once the stream is closed there is no arrival pace left to smooth out, and
// trickling out the rest would just be delay for its own sake.
function createTypewriter(getBodyEl, { wordDelayMs = 12, onDone } = {}) {
  let raw = "";
  let shown = 0;
  let tokens = [];
  let finalText = null;
  let timer = null;
  let doneFired = false;

  function retokenize() {
    tokens = raw.match(/\s+|\S+/g) || [];
  }

  function paint() {
    const body = getBodyEl();
    if (body) body.innerHTML = renderMarkdown(tokens.slice(0, shown).join(""));
    stickToBottom();
  }

  function tick() {
    // Never reveal the very last token until either more text has arrived
    // after it (so it's no longer last) or finish() confirms it's complete —
    // otherwise a word gets painted mid-character as its delta trickles in.
    const revealLimit = finalText !== null ? tokens.length : Math.max(0, tokens.length - 1);
    if (shown >= revealLimit) {
      timer = null;
      if (finalText !== null && !doneFired) { doneFired = true; onDone?.(); }
      return;
    }
    shown++;
    paint();
    timer = setTimeout(tick, wordDelayMs);
  }

  function ensureTimer() {
    if (!timer) timer = setTimeout(tick, wordDelayMs);
  }

  return {
    push(deltaText) {
      raw += deltaText;
      retokenize();
      ensureTimer();
    },
    // Everything streamed so far turned out to be the agent narrating its plan
    // between tool calls rather than the answer (the server says so with a
    // 'text_reset'), so drop it and start the answer area clean.
    reset() {
      raw = "";
      shown = 0;
      tokens = [];
      finalText = null;
      if (timer) { clearTimeout(timer); timer = null; }
      paint();
    },
    // Called when the stream's own 'done' frame arrives — everything is in
    // hand at this point, so paint it all and stop the reveal rather than
    // trickling out the remainder on a timer the data no longer justifies.
    finish(text) {
      finalText = text;
      raw = text;
      retokenize();
      if (timer) { clearTimeout(timer); timer = null; }
      shown = tokens.length;
      paint();
      if (!doneFired) { doneFired = true; onDone?.(); }
    },
  };
}

function addMessage(role, contentHtml, extraClass, customTime) {
  chatPanel.classList.remove("is-empty");
  const wrap = document.createElement("div");
  wrap.className = `msg ${role}${extraClass ? " " + extraClass : ""}`;
  const avatarLabel = role === "user" ? USER_INITIALS : "AI";
  const time = customTime || new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  wrap.innerHTML = `
    <div class="msg-avatar">${avatarLabel}</div>
    <div class="msg-body">
      <div class="msg-content">${contentHtml}</div>
      <div class="msg-time">${time}</div>
    </div>`;
  chatWindow.appendChild(wrap);
  // Follow only if the reader has not opted out. Sending a question resets
  // that opt-out explicitly at the call site, since that is the user's own
  // action; a card appended by the incoming stream must not.
  stickToBottom();
  updateJumpLatestButton();
  return wrap;
}

// Copy / Edit / Regenerate buttons below the user's own question bubble.
// Copy copies the raw question text; Edit loads it back into the chat input
// for editing (and re-sending); Regenerate re-asks the exact same question.
function addUserRegenerateButton(msgEl, question) {
  const body = msgEl.querySelector(".msg-body");
  if (!body) return;
  const row = document.createElement("div");
  row.className = "msg-actions";
  row.innerHTML = `
    <button class="action-btn copy-btn" type="button" title="Copy" aria-label="Copy">${ICON_COPY}</button>
    <button class="action-btn edit-btn" type="button" title="Edit" aria-label="Edit">${ICON_EDIT}</button>
    <button class="action-btn regen-btn" type="button" title="Regenerate" aria-label="Regenerate">${ICON_REGEN}</button>`;
  body.appendChild(row);

  const copyBtn = row.querySelector(".copy-btn");
  copyBtn.addEventListener("click", () => {
    navigator.clipboard.writeText(question || "").catch(() => {});
    copyBtn.innerHTML = ICON_CHECK;
    copyBtn.classList.add("copied");
    setTimeout(() => {
      copyBtn.innerHTML = ICON_COPY;
      copyBtn.classList.remove("copied");
    }, 1400);
  });

  row.querySelector(".edit-btn").addEventListener("click", () => {
    chatInput.value = question;
    autoResizeTextarea();
    chatInput.focus();
    const len = chatInput.value.length;
    chatInput.setSelectionRange(len, len);
  });

  row.querySelector(".regen-btn").addEventListener("click", () => {
    if (!isProcessing) askQuestion(question);
  });
}

// ---------------------------------------------------------------------------
// Conversation history (sidebar Recents list). Persisted server-side per
// Windows user, so it survives page reloads and is loaded fresh on every
// visit (see window.__INITIAL_HISTORY__, rendered by the server in index.html).
// Each Recents item is a whole conversation — clicking it opens every
// question/answer asked in that session, never a single message.
// ---------------------------------------------------------------------------
const sessionHistory = (Array.isArray(window.__INITIAL_HISTORY__) ? window.__INITIAL_HISTORY__ : [])
  .filter((c) => c && Array.isArray(c.messages))
  .map((c) => ({
    conversationId: c.conversation_id,
    title: c.title || (c.messages[0] && c.messages[0].question) || "",
    updatedAt: c.updated_at || null,
    archived: !!c.archived,
    messages: c.messages.map((m) => ({
      id: m.id || null, question: m.question, answer: m.answer || "", timestamp: m.timestamp || null,
      hasSql: m.has_sql !== undefined ? m.has_sql : true, // entries logged before this field existed: assume database-sourced
      sql: m.sql || null,
      columns: m.columns || null,
      rows: m.rows || null,
      tableTitle: m.table_title || null,
      chart: m.chart || null,
      vegaSpec: m.vega_spec || null,
      usage: m.usage || null,
      elapsed: m.elapsed != null ? m.elapsed : null,
      relevancePercent: m.relevance_percent != null ? m.relevance_percent : null,
      steps: m.reasoning_steps || [],
    })),
  }));
// [{conversationId, title, updatedAt, messages: [{id, question, answer, timestamp, hasSql}]}]
// Total tokens/cost are tracked separately, per call with no dedup, via /api/usage.

// A random id per conversation "thread" — sent with every /api/chat call so
// the backend groups messages together. Regenerated on "New chat" (and once
// at load, for whatever the user asks before ever clicking New chat).
let currentConversationId = crypto.randomUUID();

// Conversational context for follow-up suggestions/replies — scoped to the
// current thread only, so "New chat" resets it without touching the
// persisted Recents list (sessionHistory) above.
let currentThreadHistory = [];

function addToHistory(question) {
  let conv = sessionHistory.find((c) => c.conversationId === currentConversationId);
  if (!conv) {
    conv = { conversationId: currentConversationId, title: question, updatedAt: null, archived: false, messages: [] };
    sessionHistory.push(conv);
  }
  const entry = { id: null, question, answer: "", timestamp: new Date().toISOString() };
  conv.messages.push(entry);
  conv.updatedAt = entry.timestamp;
  currentThreadHistory.push(entry); // same object reference — later answer/id updates are shared
  renderHistorySidebar();
  return entry;
}

function deleteConversation(conversationId) {
  const idx = sessionHistory.findIndex((c) => c.conversationId === conversationId);
  if (idx === -1) return;
  sessionHistory.splice(idx, 1);
  renderHistorySidebar();
  fetch("/api/history/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId }),
  }).catch(() => {});
}

let archiveExpanded = false;

function archiveConversation(conversationId, archived) {
  const conv = sessionHistory.find((c) => c.conversationId === conversationId);
  if (!conv || conv.archived === archived) return;
  conv.archived = archived;
  renderHistorySidebar();
  fetch("/api/history/archive", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, archived }),
  }).catch(() => {});
}

function formatHistoryTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString([], { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

// Filters out any suggestion that duplicates a question already asked this
// session, or that duplicates another suggestion in the same batch.
function dedupeSuggestions(suggestions) {
  if (!suggestions || !suggestions.length) return [];
  const asked = new Set(sessionHistory.flatMap((c) => c.messages).map((h) => h.question.trim().toLowerCase()));
  const seen = new Set();
  const out = [];
  for (const s of suggestions) {
    const key = String(s).trim().toLowerCase();
    if (!key || asked.has(key) || seen.has(key)) continue;
    seen.add(key);
    out.push(s);
  }
  return out;
}

function historyItemHtml(c) {
  const toggleIcon = c.archived ? ICON_RESTORE : ICON_ARCHIVE;
  const toggleTitle = c.archived ? "Restore to Recents" : "Archive";
  return `
    <div class="history-item" draggable="true" data-conversation-id="${escapeHtml(c.conversationId)}" title="${escapeHtml(c.title)}">
      <button class="history-q" type="button">
        <span class="history-q-text">${escapeHtml(c.title)}</span>
        <span class="history-q-time">
          ${c.messages.length > 1 ? `${c.messages.length} messages · ` : ""}${escapeHtml(formatHistoryTime(c.updatedAt))}
        </span>
      </button>
      <div class="history-actions">
        <button class="history-edit" type="button" title="Rename" aria-label="Rename">${ICON_EDIT}</button>
        <button class="history-archive-btn" type="button" title="${toggleTitle}" aria-label="${toggleTitle}">${toggleIcon}</button>
        <button class="history-delete" type="button" title="Delete" aria-label="Delete">${ICON_TRASH}</button>
      </div>
    </div>`;
}

function wireHistoryItemRow(row) {
  const conversationId = row.dataset.conversationId;
  row.querySelector(".history-q").addEventListener("click", () => displayConversation(conversationId));
  row.querySelector(".history-edit").addEventListener("click", (e) => {
    e.stopPropagation();
    const editBtn = e.currentTarget;
    if (editBtn.classList.contains("is-editing")) {
      row.querySelector(".history-q-rename-input")?.blur(); // commits (see startRenameConversation)
    } else {
      startRenameConversation(row, conversationId);
    }
  });
  row.querySelector(".history-delete").addEventListener("click", (e) => {
    e.stopPropagation();
    deleteConversation(conversationId);
  });
  row.querySelector(".history-archive-btn").addEventListener("click", (e) => {
    e.stopPropagation();
    const conv = sessionHistory.find((c) => c.conversationId === conversationId);
    if (conv) archiveConversation(conversationId, !conv.archived);
  });
  row.addEventListener("dragstart", (e) => {
    e.dataTransfer.setData("text/plain", conversationId);
    e.dataTransfer.effectAllowed = "move";
    row.classList.add("dragging");
  });
  row.addEventListener("dragend", () => row.classList.remove("dragging"));
}

function renderHistoryGroup(listEl, items, query, emptyHtml) {
  if (!items.length) {
    listEl.innerHTML = emptyHtml;
    return;
  }
  const filtered = query
    ? items.filter((c) =>
        c.title.toLowerCase().includes(query) || c.messages.some((m) => m.question.toLowerCase().includes(query)))
    : items;
  if (!filtered.length) {
    listEl.innerHTML = `<p class="muted history-no-match">No matches.</p>`;
    return;
  }
  listEl.innerHTML = filtered.map(historyItemHtml).join("");
  listEl.querySelectorAll(".history-item").forEach(wireHistoryItemRow);
}

function renderHistorySidebar() {
  const query = (historySearch?.value || "").trim().toLowerCase();
  const ordered = sessionHistory.slice().sort((a, b) => (b.updatedAt || "").localeCompare(a.updatedAt || ""));
  const recents = ordered.filter((c) => !c.archived);
  const archived = ordered.filter((c) => c.archived);

  renderHistoryGroup(
    document.getElementById("history-list"), recents, query,
    `<p class="muted history-empty" id="history-empty">No questions yet this session.</p>`
  );
  renderHistoryGroup(
    document.getElementById("archive-list"), archived, query,
    `<p class="muted history-empty">No archived chats.</p>`
  );

  const archiveToggle = document.getElementById("archive-toggle");
  const archiveCount = document.getElementById("archive-count");
  const archiveFolderIcon = document.getElementById("archive-folder-icon");
  if (archiveCount) archiveCount.textContent = archived.length ? String(archived.length) : "";
  if (archiveFolderIcon) archiveFolderIcon.innerHTML = archiveExpanded ? ICON_FOLDER_OPEN : ICON_FOLDER_CLOSED;
  archiveToggle?.setAttribute("aria-expanded", String(archiveExpanded));
  archiveToggle?.classList.toggle("has-items", archived.length > 0);
  document.getElementById("archive-folder-body")?.toggleAttribute("hidden", !archiveExpanded);
}
renderHistorySidebar();

// Drag-and-drop archiving: dropping a Recents item onto the Archive header
// (or its expanded list) archives it; dropping an archived item back onto
// Recents restores it. Set up once — these container elements are never
// recreated, only their innerHTML (and therefore their .history-item
// children) is replaced on each render.
function setupArchiveDropTarget(el, archived) {
  if (!el) return;
  el.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    el.classList.add("drag-over");
  });
  el.addEventListener("dragleave", () => el.classList.remove("drag-over"));
  el.addEventListener("drop", (e) => {
    e.preventDefault();
    el.classList.remove("drag-over");
    const conversationId = e.dataTransfer.getData("text/plain");
    if (conversationId) archiveConversation(conversationId, archived);
  });
}
setupArchiveDropTarget(document.getElementById("archive-toggle"), true);
setupArchiveDropTarget(document.getElementById("archive-list"), true);
setupArchiveDropTarget(document.getElementById("recents-heading"), false);
setupArchiveDropTarget(document.getElementById("history-list"), false);

document.getElementById("archive-toggle")?.addEventListener("click", () => {
  archiveExpanded = !archiveExpanded;
  renderHistorySidebar();
});

function renameConversation(conversationId, title) {
  const conv = sessionHistory.find((c) => c.conversationId === conversationId);
  if (!conv) return;
  conv.title = title;
  renderHistorySidebar();
  fetch("/api/history/rename", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, title }),
  }).catch(() => {});
}

function startRenameConversation(row, conversationId) {
  const conv = sessionHistory.find((c) => c.conversationId === conversationId);
  if (!conv) return;
  const textEl = row.querySelector(".history-q-text");
  const editBtn = row.querySelector(".history-edit");
  const actions = row.querySelector(".history-actions");

  const input = document.createElement("input");
  input.type = "text";
  input.className = "history-q-rename-input";
  input.value = conv.title;
  textEl.replaceWith(input);
  input.focus();
  input.select();

  editBtn.innerHTML = ICON_CHECK;
  editBtn.classList.add("is-editing");
  editBtn.title = "Save";
  editBtn.setAttribute("aria-label", "Save");
  actions?.classList.add("force-visible");

  let done = false;
  function commit() {
    if (done) return;
    done = true;
    const newTitle = input.value.trim();
    if (newTitle && newTitle !== conv.title) {
      renameConversation(conversationId, newTitle);
    } else {
      renderHistorySidebar();
    }
  }
  input.addEventListener("keydown", (e) => {
    e.stopPropagation();
    if (e.key === "Enter") { e.preventDefault(); input.blur(); }
    else if (e.key === "Escape") { e.preventDefault(); done = true; renderHistorySidebar(); }
  });
  input.addEventListener("click", (e) => e.stopPropagation());
  input.addEventListener("blur", commit);
}

// Clicking a Recents item opens the whole saved conversation as-is — it
// never re-queries Snowflake. (Regenerate, in each answer's action row, is
// the opt-in way to re-run a given question live.) Typing a new message
// afterward continues this same conversation.
function displayConversation(conversationId) {
  if (isProcessing) return;
  const conv = sessionHistory.find((c) => c.conversationId === conversationId);
  if (!conv) return;

  clearFollowupSuggestions();
  chatWindow.querySelectorAll(".msg, .planning-card").forEach((el) => el.remove());
  chatPanel.classList.remove("is-empty");

  for (const entry of conv.messages) {
    const time = formatHistoryTime(entry.timestamp);
    const userEl = addMessage("user", escapeHtml(entry.question), null, time);
    addUserRegenerateButton(userEl, entry.question);
    if (entry.steps && entry.steps.length) {
      const planCard = createPlanningCard();
      entry.steps.forEach((step) => planCard.addThinkingParagraph(step));
      planCard.complete();
    }
    const { html } = buildAnswerHtml(entry);
    const assistantEl = addMessage("assistant", html, null, time);
    attachCollapsibles(assistantEl, entry);
    mountAnswerChart(assistantEl, entry);
    attachClarifyingOptions(assistantEl);
    attachActionRow(assistantEl, {
      interactionId: entry.id,
      question: entry.question,
      answer: entry.answer,
      isAgent: true,
      columns: entry.columns,
      rows: entry.rows,
    });
  }

  currentConversationId = conversationId;
  currentThreadHistory = conv.messages.slice();
  historyNavIndex = -1;
  draftBeforeNav = "";
}

historySearch?.addEventListener("input", () => renderHistorySidebar());

// Follow-up suggestions from the latest answer float above the composer
// (like Claude's follow-up prompts) instead of living inline in the answer
// bubble — there's only ever one batch shown at a time, for the most recent
// answer, cleared as soon as a new question starts.
function renderFollowupSuggestions(suggestions) {
  const deduped = dedupeSuggestions(suggestions);
  if (!followupSuggestions || !deduped.length) {
    clearFollowupSuggestions();
    return;
  }
  followupSuggestions.innerHTML = deduped.map((s) =>
    `<button class="suggestion-chip" type="button" title="${escapeHtml(s)}">${escapeHtml(s)}</button>`
  ).join("");
  followupSuggestions.hidden = false;
  followupSuggestions.querySelectorAll(".suggestion-chip").forEach((btn, i) => {
    btn.addEventListener("click", () => {
      clearFollowupSuggestions();
      askQuestion(deduped[i]);
    });
  });
}

function clearFollowupSuggestions() {
  if (!followupSuggestions) return;
  followupSuggestions.hidden = true;
  followupSuggestions.innerHTML = "";
}

// ---------------------------------------------------------------------------
// Busy state: only one question in flight at a time. While processing, the
// send button becomes a Stop button (aborts the fetch) and every question
// entry point (input, sample/history/suggestion chips) is inert.
// ---------------------------------------------------------------------------
let isProcessing = false;
let currentAbortController = null;

function setProcessing(state) {
  isProcessing = state;
  chatSend.innerHTML = state ? STOP_ICON : SEND_ICON;
  chatSend.classList.toggle("stop-mode", state);
  chatSend.setAttribute("aria-label", state ? "Stop" : "Send");
  document.body.classList.toggle("chat-busy", state);
}

function buildActionRowHtml(isAgent) {
  return `
  <div class="msg-actions">
    <button class="action-btn copy-btn" type="button" title="Copy" aria-label="Copy">${ICON_COPY}</button>
    ${isAgent ? `<button class="action-btn regen-btn" type="button" title="Regenerate" aria-label="Regenerate">${ICON_REGEN}</button>` : ""}
    <button class="action-btn download-btn" type="button" title="Download as PDF" aria-label="Download as PDF">${ICON_DOWNLOAD}</button>
    <span class="action-divider" aria-hidden="true"></span>
    <button class="action-btn feedback-btn up" type="button" title="Good response" aria-label="Good response">${ICON_THUMB_UP}</button>
    <button class="action-btn feedback-btn down" type="button" title="Bad response" aria-label="Bad response">${ICON_THUMB_DOWN}</button>
    <span class="feedback-note" hidden>Thanks for the feedback!</span>
  </div>`;
}

// "Top suppliers by excess value" -> "top-suppliers-by-excess-value"
function slugify(text, maxLen = 50) {
  return String(text).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, maxLen) || "chat";
}

// jsPDF's text APIs don't understand markdown — instead of stripping it down
// to flat plain text (which lost all the on-screen formatting), parse the
// answer into blocks (headings/paragraphs/lists/tables) and inline bold runs,
// then render each with the matching PDF styling so bold stays bold, headings
// stay bigger, lists stay bulleted, and any markdown table in the prose gets
// its own real table — not just the SQL result table.
function parseMarkdownBlocksForPdf(text) {
  const lines = String(text).replace(/\\~/g, "~").split("\n");
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }

    if (/^\s*\|.*\|\s*$/.test(line)) {
      const tableLines = [];
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) {
        tableLines.push(lines[i].trim());
        i++;
      }
      const parsed = tableLines
        .filter((l) => !/^\|[\s:|-]+\|$/.test(l)) // drop the "|---|---|" separator row
        .map((l) => l.replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim()));
      if (parsed.length) blocks.push({ type: "table", header: parsed[0], rows: parsed.slice(1) });
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.*)/);
    if (heading) {
      blocks.push({ type: "heading", level: heading[1].length, text: heading[2] });
      i++;
      continue;
    }

    const listItem = line.match(/^\s*(?:[-*+]|\d+[.)])\s+(.*)/);
    if (listItem) {
      blocks.push({ type: "list", text: listItem[1] });
      i++;
      continue;
    }

    const paraLines = [line];
    i++;
    while (
      i < lines.length && lines[i].trim() &&
      !/^\s*\|.*\|\s*$/.test(lines[i]) && !/^#{1,6}\s/.test(lines[i]) && !/^\s*(?:[-*+]|\d+[.)])\s/.test(lines[i])
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    blocks.push({ type: "paragraph", text: paraLines.join(" ") });
  }
  return blocks;
}

// "some **bold** text" -> [{text:"some ", bold:false}, {text:"bold", bold:true}, {text:" text", bold:false}]
function parseInlineSegmentsForPdf(text) {
  const clean = String(text).replace(/`([^`]+)`/g, "$1");
  const segments = [];
  const re = /\*\*([^*]+)\*\*/g;
  let last = 0, m;
  while ((m = re.exec(clean))) {
    if (m.index > last) segments.push({ text: clean.slice(last, m.index), bold: false });
    segments.push({ text: m[1], bold: true });
    last = re.lastIndex;
  }
  if (last < clean.length) segments.push({ text: clean.slice(last), bold: false });
  return segments;
}

// Word-wraps a run of mixed bold/normal segments across lines/pages, since
// jsPDF has no built-in rich-text flow.
function renderRichTextForPdf(doc, segments, x, maxWidth, y, lineHeight, pageBottom, pageTop) {
  let curX = x;
  let curY = y;
  for (const seg of segments) {
    doc.setFont("helvetica", seg.bold ? "bold" : "normal");
    for (const word of seg.text.split(/(\s+)/).filter((w) => w.length)) {
      if (/^\s+$/.test(word)) {
        curX += doc.getTextWidth(word);
        continue;
      }
      const w = doc.getTextWidth(word);
      if (curX + w > x + maxWidth && curX > x) {
        curY += lineHeight;
        curX = x;
      }
      if (curY > pageBottom) {
        doc.addPage();
        curY = pageTop;
        curX = x;
      }
      doc.text(word, curX, curY);
      curX += w;
    }
  }
  return curY + lineHeight;
}

// Rasterizes a live Vega-Lite SVG (drawn by vega-embed) into a PNG data URL
// so it can be dropped into the PDF the same way a Chart.js canvas can via
// canvas.toDataURL() — jsPDF's addImage only understands raster images.
async function svgToPngDataUrl(svgEl, scale = 2) {
  const xml = new XMLSerializer().serializeToString(svgEl);
  const url = URL.createObjectURL(new Blob([xml], { type: "image/svg+xml;charset=utf-8" }));
  try {
    const img = await new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = reject;
      image.src = url;
    });
    const canvas = document.createElement("canvas");
    canvas.width = (img.width || svgEl.clientWidth || 600) * scale;
    canvas.height = (img.height || svgEl.clientHeight || 320) * scale;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = "#ffffff"; // the SVG background is transparent; the PDF page is white
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/png");
  } finally {
    URL.revokeObjectURL(url);
  }
}

// Grabs whatever chart is already rendered on screen for this answer (a
// Chart.js <canvas> or a vega-embed <svg>) as a PNG data URL — reuses the
// already-rendered visual instead of re-rendering the chart from scratch.
async function captureChartImage(chartWrapEl) {
  if (!chartWrapEl) return null;
  const canvas = chartWrapEl.querySelector("canvas");
  if (canvas) {
    try { return canvas.toDataURL("image/png"); } catch { return null; }
  }
  const svg = chartWrapEl.querySelector("svg");
  if (svg) {
    try { return await svgToPngDataUrl(svg); } catch { return null; }
  }
  return null;
}

// PDF contains the user's question, the assistant's answer/table, and its
// chart (if the answer has one) — no SQL, planning trace, or usage stats.
async function downloadAnswerAsPdf({ question, answer, columns, rows, chartEl }) {
  if (!window.jspdf) return;
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "pt" });
  const margin = 40;
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const maxWidth = pageWidth - margin * 2;
  const pageBottom = pageHeight - margin;
  let y = margin;

  function ensureRoom(h) {
    if (y > pageBottom - h) {
      doc.addPage();
      y = margin;
    }
  }

  doc.setFont("helvetica", "bold");
  doc.setFontSize(13);
  for (const line of doc.splitTextToSize(question, maxWidth)) {
    ensureRoom(18);
    doc.text(line, margin, y);
    y += 18;
  }
  y += 10;

  for (const block of parseMarkdownBlocksForPdf(answer || "")) {
    if (block.type === "table") {
      y += 6;
      ensureRoom(40);
      doc.autoTable({
        startY: y,
        head: [block.header],
        body: block.rows,
        margin: { left: margin, right: margin },
        tableWidth: maxWidth,
        styles: { fontSize: 8, cellPadding: 4, overflow: "linebreak" },
        headStyles: { fillColor: [11, 31, 59] },
        columnStyles: pdfNumericColumnStyles(block.rows),
      });
      y = doc.lastAutoTable.finalY + 10;
      continue;
    }

    if (block.type === "heading") {
      doc.setFontSize(block.level <= 2 ? 13 : 11.5);
      ensureRoom(18);
      y = renderRichTextForPdf(doc, [{ text: block.text, bold: true }], margin, maxWidth, y, 16, pageBottom, margin);
      y += 4;
      continue;
    }

    doc.setFontSize(11);
    if (block.type === "list") {
      ensureRoom(15);
      doc.setFont("helvetica", "normal");
      doc.text("•", margin, y);
      y = renderRichTextForPdf(doc, parseInlineSegmentsForPdf(block.text), margin + 14, maxWidth - 14, y, 15, pageBottom, margin);
    } else {
      ensureRoom(15);
      y = renderRichTextForPdf(doc, parseInlineSegmentsForPdf(block.text), margin, maxWidth, y, 15, pageBottom, margin);
      y += 6;
    }
  }

  // Chart goes in the same spot as on screen: above the table.
  const chartImg = await captureChartImage(chartEl);
  if (chartImg) {
    const props = doc.getImageProperties(chartImg);
    const imgWidth = maxWidth;
    const imgHeight = (props.height / props.width) * imgWidth;
    y += 6;
    ensureRoom(imgHeight);
    doc.addImage(chartImg, "PNG", margin, y, imgWidth, imgHeight);
    y += imgHeight + 10;
  }

  if (columns && columns.length && rows && rows.length) {
    y += 6;
    ensureRoom(40);
    doc.autoTable({
      startY: y,
      head: [columns],
      body: rows.map((r) => r.map((v) => (v === null || v === undefined ? "" : String(v)))),
      margin: { left: margin, right: margin },
      tableWidth: maxWidth,
      styles: { fontSize: 8, cellPadding: 4, overflow: "linebreak" },
      headStyles: { fillColor: [11, 31, 59] },
      columnStyles: pdfNumericColumnStyles(rows),
    });
  }

  const stamp = new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-");
  doc.save(`eno-chat_${slugify(question)}_${stamp}.pdf`);
}

// Whole current conversation (every question + its main agent answer, in
// order) as one PDF — same block-by-block markdown rendering as the
// per-answer export above, just looped, with a rule between Q&A pairs and
// page breaks handled the same way (ensureRoom).
async function downloadConversationAsPdf() {
  if (!window.jspdf || !currentThreadHistory.length) return;
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "pt" });
  const margin = 40;
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const maxWidth = pageWidth - margin * 2;
  const pageBottom = pageHeight - margin;
  let y = margin;

  function ensureRoom(h) {
    if (y > pageBottom - h) {
      doc.addPage();
      y = margin;
    }
  }

  currentThreadHistory.forEach((entry, i) => {
    if (i > 0) {
      ensureRoom(24);
      y += 6;
      doc.setDrawColor(200);
      doc.line(margin, y, pageWidth - margin, y);
      y += 18;
    }

    doc.setFont("helvetica", "bold");
    doc.setFontSize(13);
    for (const line of doc.splitTextToSize(entry.question || "", maxWidth)) {
      ensureRoom(18);
      doc.text(line, margin, y);
      y += 18;
    }
    y += 10;

    for (const block of parseMarkdownBlocksForPdf(entry.answer || "")) {
      if (block.type === "table") {
        y += 6;
        ensureRoom(40);
        doc.autoTable({
          startY: y,
          head: [block.header],
          body: block.rows,
          margin: { left: margin, right: margin },
          tableWidth: maxWidth,
          styles: { fontSize: 8, cellPadding: 4, overflow: "linebreak" },
          headStyles: { fillColor: [11, 31, 59] },
          columnStyles: pdfNumericColumnStyles(block.rows),
        });
        y = doc.lastAutoTable.finalY + 10;
        continue;
      }

      if (block.type === "heading") {
        doc.setFontSize(block.level <= 2 ? 13 : 11.5);
        ensureRoom(18);
        y = renderRichTextForPdf(doc, [{ text: block.text, bold: true }], margin, maxWidth, y, 16, pageBottom, margin);
        y += 4;
        continue;
      }

      doc.setFontSize(11);
      if (block.type === "list") {
        ensureRoom(15);
        doc.setFont("helvetica", "normal");
        doc.text("•", margin, y);
        y = renderRichTextForPdf(doc, parseInlineSegmentsForPdf(block.text), margin + 14, maxWidth - 14, y, 15, pageBottom, margin);
      } else {
        ensureRoom(15);
        y = renderRichTextForPdf(doc, parseInlineSegmentsForPdf(block.text), margin, maxWidth, y, 15, pageBottom, margin);
        y += 6;
      }
    }

    if (entry.columns && entry.columns.length && entry.rows && entry.rows.length) {
      y += 6;
      ensureRoom(40);
      doc.autoTable({
        startY: y,
        head: [entry.columns],
        body: entry.rows.map((r) => r.map((v) => (v === null || v === undefined ? "" : String(v)))),
        margin: { left: margin, right: margin },
        tableWidth: maxWidth,
        styles: { fontSize: 8, cellPadding: 4, overflow: "linebreak" },
        headStyles: { fillColor: [11, 31, 59] },
        columnStyles: pdfNumericColumnStyles(entry.rows),
      });
      y = doc.lastAutoTable.finalY;
    }
    y += 10;
  });

  const stamp = new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-");
  doc.save(`eno-chat_conversation_${stamp}.pdf`);
}

function attachActionRow(msgEl, { interactionId, question, answer, columns, rows }) {
  const copyBtn = msgEl.querySelector(".copy-btn");
  copyBtn?.addEventListener("click", () => {
    navigator.clipboard.writeText(answer || "").catch(() => {});
    copyBtn.innerHTML = ICON_CHECK;
    copyBtn.classList.add("copied");
    setTimeout(() => {
      copyBtn.innerHTML = ICON_COPY;
      copyBtn.classList.remove("copied");
    }, 1400);
  });

  const downloadBtn = msgEl.querySelector(".download-btn");
  downloadBtn?.addEventListener("click", () => downloadAnswerAsPdf({
    question, answer, columns, rows, chartEl: msgEl.querySelector(".answer-chart-wrap"),
  }));

  const regenBtn = msgEl.querySelector(".regen-btn");
  regenBtn?.addEventListener("click", () => {
    if (!isProcessing) askQuestion(question);
  });

  const upBtn = msgEl.querySelector(".feedback-btn.up");
  const downBtn = msgEl.querySelector(".feedback-btn.down");
  const note = msgEl.querySelector(".feedback-note");
  let active = null; // "up" | "down" | null

  function setActive(rating) {
    active = rating;
    upBtn.classList.toggle("active", rating === "up");
    downBtn.classList.toggle("active", rating === "down");
    if (note) note.hidden = !rating;
  }

  function handleClick(rating) {
    if (active === rating) {
      setActive(null); // deactivating does not call the API
      return;
    }
    setActive(rating);
    fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ interaction_id: interactionId, rating, question, answer }),
    }).catch(() => {});
  }

  upBtn?.addEventListener("click", () => handleClick("up"));
  downBtn?.addEventListener("click", () => handleClick("down"));
}

// Everything that follows the answer's own markdown text — chart, result
// table, SQL dropdown, action row, usage stats. Split out from buildAnswerHtml
// so a streamed answer (whose markdown div is already in the DOM and filled
// in progressively as text_delta events arrive) can have this appended once
// streaming finishes, without re-inserting (and so re-triggering) the text.
function buildAnswerExtrasHtml(data, isAgent = true) {
  const tableId   = uid("tbl");
  const sqlId     = uid("sql");
  const chartId   = uid("chart");
  const graphId   = uid("graph");
  const tableHtml = renderResultTable(data.columns, data.rows);
  const rowCount  = (data.rows || []).length;
  // Only offer the Graph view dropdown when a graph can actually be built
  // from this table (e.g. it has a non-numeric "dimension" column and 2+
  // distinct entities) — otherwise skip the button entirely rather than
  // showing it and then revealing an empty/"not enough entities" state.
  // The graph is fetched from /api/subgraph, which recognises entities by
  // their pseudonym prefix, so offer the dropdown whenever the result has
  // any rows at all rather than pre-guessing from the column shape.
  const canBuildGraph = !!(data.rows && data.rows.length);
  const agentChart = data.chart || null;
  const hasAgentChart = !!(data.vegaSpec || agentChart);
  const tableLabel = data.tableTitle
    ? `${escapeHtml(data.tableTitle)} (${rowCount} row${rowCount === 1 ? "" : "s"})`
    : `Database output (${rowCount} row${rowCount === 1 ? "" : "s"})`;
  const chartLabel = data.vegaSpec
    ? (data.vegaSpec.title || "Chart")
    : agentChart
    ? (agentChart.title || `${agentChart.yTitle || ""}${agentChart.yTitle && agentChart.xTitle ? " by " : ""}${agentChart.xTitle || ""}` || "Chart")
    : "";

  // Only a real chart from the agent's own Snowflake payload (vegaSpec/
  // chart) is ever shown — no client-guessed "suggested" chart — and it
  // renders inline below the response, always visible, no collapsible link.
  const chartBlock = hasAgentChart ? `
    <div class="answer-chart-label">${escapeHtml(chartLabel)}</div>
    <div class="answer-chart-wrap" id="${chartId}">${data.vegaSpec ? "<div class=\"vega-wrap\"></div>" : "<canvas></canvas>"}</div>`
    : "";

  return `
    ${chartBlock}
    ${tableHtml ? `
    <button class="collapsible-toggle" data-target="${tableId}">
      <span class="chevron">▸</span> ${tableLabel}
    </button>
    <div id="${tableId}" style="display:none">${tableHtml}</div>` : ""}
    ${canBuildGraph ? `
    <button class="collapsible-toggle graph-toggle" data-target="${graphId}">
      <span class="chevron">▸</span> Graph view
    </button>
    <div id="${graphId}" style="display:none"><div class="answer-graph-wrap"></div></div>` : ""}
    ${data.sql ? `
    <button class="collapsible-toggle" data-target="${sqlId}">
      <span class="chevron">▸</span> SQL query
    </button>
    <div id="${sqlId}" style="display:none"><pre class="code-block"><code class="language-sql">${escapeHtml(data.sql)}</code></pre></div>` : ""}
    ${buildActionRowHtml(isAgent)}`;
}



function buildAnswerHtml(data, isAgent = true) {
  return { html: `
    ${isAgent ? '<div class="answer-chart-label">KG answer</div>' : ""}
    <div class="msg-text markdown-body">${renderMarkdown(data.answer)}</div>
    ${buildAnswerExtrasHtml(data, isAgent)}` };
}

// The agent sometimes asks a clarifying question inline in its answer prose
// ("Which site would you like this for?") followed by a plain markdown
// bullet list of short options ("Site 059", "Site 867", ...) — that's a
// different mechanism than the suggested_queries/"suggestions" follow-ups
// (which only ever come after a completed answer), so it never reaches
// renderFollowupSuggestions. Detect that specific shape here instead — a
// short list whose preceding paragraph ends in "?" — and make each option
// clickable, submitting its exact text as the reply to the clarifying
// question, same as the follow-up suggestion chips do.
function attachClarifyingOptions(msgEl) {
  const body = msgEl.querySelector(".markdown-body");
  if (!body) return;
  body.querySelectorAll("ul, ol").forEach((list) => {
    const items = [...list.querySelectorAll(":scope > li")];
    if (!items.length || items.length > 8) return;
    const prev = list.previousElementSibling;
    const looksLikeQuestion = prev && /\?\s*$/.test(prev.textContent.trim());
    const itemsAreShort = items.every((li) => li.textContent.trim().length <= 60);
    if (!looksLikeQuestion || !itemsAreShort) return;
    list.classList.add("clarify-options");
    items.forEach((li) => {
      const text = li.textContent.trim();
      li.setAttribute("role", "button");
      li.tabIndex = 0;
      li.addEventListener("click", () => { if (!isProcessing) askQuestion(text); });
      li.addEventListener("keydown", (e) => {
        if ((e.key === "Enter" || e.key === " ") && !isProcessing) { e.preventDefault(); askQuestion(text); }
      });
    });
  });
}

// `data` is optional — only the .graph-toggle button uses it, to lazily
// build+mount the Cytoscape graph the first time it's expanded (Cytoscape
// needs a visible, sized container to lay out correctly, so it can't be
// mounted while display:none).
function attachCollapsibles(msgEl, data) {
  msgEl.querySelectorAll(".collapsible-toggle").forEach((btn) => {
    // A section nested in the shared answer card can be swept twice — once by
    // its own section call, once by the card-wide one. Two listeners means a
    // click opens and immediately closes again, so the first binding wins.
    if (btn.dataset.collapsibleBound) return;
    btn.dataset.collapsibleBound = "1";
    btn.addEventListener("click", () => {
      const target = document.getElementById(btn.dataset.target);
      const expanding = target.style.display === "none";
      target.style.display = expanding ? "block" : "none";
      btn.classList.toggle("expanded", expanding);
      if (expanding && btn.classList.contains("graph-toggle") && data) {
        mountAnswerGraph(target.querySelector(".answer-graph-wrap"), data);
      }
      // Opening a section is the reader's own action, so following it down is
      // expected — but only when they were already at the bottom.
      if (expanding) revealAnswerEnd();
    });
  });
}

// ---------------------------------------------------------------------------
// Graph view: derives a node-link diagram straight from the answer's own
// result table (columns/rows) — no extra Snowflake round-trip. A column is a
// "dimension" (becomes nodes) if it's not all-numeric across every row; a
// "measure" (EXCESS_USD, etc.) never becomes a node. Rows with 2+ dimension
// values co-occurring get an edge between them; rows with just 1 dimension
// value get an edge to a shared hub node instead, so single-dimension tables
// still render as a meaningful (star) graph rather than scattered dots.
// ---------------------------------------------------------------------------
function classifyGraphColumns(columns, rows) {
  const dims = [];
  columns.forEach((col, i) => {
    const allNumeric = rows.every((r) => r[i] == null || typeof r[i] === "number");
    if (!allNumeric) dims.push(col);
  });
  return dims;
}

const GRAPH_NODE_CAP = 150;

function buildGraphElements(columns, rows, hubLabel) {
  if (!columns || !rows || !rows.length) return null;
  const dims = classifyGraphColumns(columns, rows);
  if (!dims.length) return null;
  const dimIndexes = dims.map((c) => columns.indexOf(c));

  const nodeMap = new Map();
  const edgeSet = new Set();
  const edges = [];
  const nodeId = (col, val) => `${col}::${val}`;
  function ensureNode(col, val, groupIndex) {
    const id = nodeId(col, val);
    if (!nodeMap.has(id)) nodeMap.set(id, { id, label: String(val), group: groupIndex, degree: 0 });
    return id;
  }
  function addEdge(a, b) {
    if (a === b) return;
    const key = a < b ? `${a}|${b}` : `${b}|${a}`;
    if (edgeSet.has(key)) return;
    edgeSet.add(key);
    edges.push({ data: { id: `e${edges.length}`, source: a, target: b } });
    nodeMap.get(a).degree++;
    nodeMap.get(b).degree++;
  }

  for (const row of rows) {
    if (nodeMap.size >= GRAPH_NODE_CAP) break;
    const rowNodeIds = [];
    for (let d = 0; d < dims.length; d++) {
      const val = row[dimIndexes[d]];
      if (val == null || val === "") continue;
      rowNodeIds.push(ensureNode(dims[d], val, d));
    }
    if (rowNodeIds.length > 1) {
      for (let a = 0; a < rowNodeIds.length; a++) {
        for (let b = a + 1; b < rowNodeIds.length; b++) addEdge(rowNodeIds[a], rowNodeIds[b]);
      }
    } else if (rowNodeIds.length === 1) {
      const hubId = "__hub__";
      if (!nodeMap.has(hubId)) nodeMap.set(hubId, { id: hubId, label: hubLabel || "Query", group: -1, degree: 0 });
      addEdge(hubId, rowNodeIds[0]);
    }
  }

  const entityCount = [...nodeMap.values()].filter((n) => n.id !== "__hub__").length;
  if (entityCount < 2) return null;
  return {
    nodes: [...nodeMap.values()].map((n) => ({ data: n })),
    edges,
    truncated: nodeMap.size >= GRAPH_NODE_CAP,
  };
}

// First 3 categorical slots only — per the dataviz palette, these are the
// ones validated for *all-pairs* simultaneous viewing (a node-link graph
// shows every node type at once, not just adjacent bars/lines). A 4th+
// dimension column folds into the muted fallback rather than cycling into
// an unvalidated slot.
const GRAPH_PALETTE_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a"];
const GRAPH_PALETTE_DARK  = ["#3987e5", "#d95926", "#199e70"];

// Draws the actual Snowflake KG subgraph behind an answer: the entities named in the
// result, plus the items, commodities, manufacturers and programs that connect
// them. Falls back to the table-derived co-occurrence graph if the server call
// fails, so the dropdown always shows something.
async function mountAnswerGraph(container, data) {
  if (!container || container.dataset.mounted === "1") return;
  container.dataset.mounted = "1";
  if (typeof cytoscape === "undefined") {
    container.innerHTML = '<p class="muted" style="padding:12px">Graph view failed to load.</p>';
    return;
  }
  container.innerHTML = '<p class="muted" style="padding:12px">Loading graph…</p>';

  let graph = null;
  try {
    const resp = await fetch("/api/subgraph", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ columns: data.columns, rows: data.rows }),
    }).then((r) => r.json());
    if (resp && Array.isArray(resp.nodes) && resp.nodes.length) {
      graph = { nodes: resp.nodes, edges: resp.edges || [], truncated: !!resp.truncated, real: true };
    }
  } catch { /* fall through to the local graph */ }

  if (!graph) graph = buildGraphElements(data.columns, data.rows, data.tableTitle);
  if (!graph) {
    container.innerHTML = '<p class="muted" style="padding:12px">No graph entities in this result to draw.</p>';
    return;
  }
  container.innerHTML = "";

  const isDark = document.documentElement.getAttribute("data-theme") === "dark"
    || (document.documentElement.getAttribute("data-theme") !== "light"
        && window.matchMedia("(prefers-color-scheme: dark)").matches);
  const palette = isDark ? GRAPH_PALETTE_DARK : GRAPH_PALETTE_LIGHT;
  const rootCs = getComputedStyle(document.documentElement);
  const textColor  = (rootCs.getPropertyValue("--text") || "").trim() || (isDark ? "#eaf1fb" : "#10192b");
  const edgeColor  = (rootCs.getPropertyValue("--border") || "").trim() || (isDark ? "#22314e" : "#dde3f0");
  const mutedColor = (rootCs.getPropertyValue("--text-muted") || "").trim() || "#5b6478";

  const cy = cytoscape({
    container,
    elements: [...graph.nodes, ...graph.edges],
    style: [
      {
        selector: "node",
        style: {
          "background-color": (ele) => {
            const g = ele.data("group");
            return g === -1 ? mutedColor : (palette[g] || mutedColor);
          },
          "label": "data(label)",
          "color": textColor,
          "font-size": 9,
          "text-valign": "bottom",
          "text-margin-y": 4,
          "width": (ele) => 16 + Math.min(28, (ele.data("degree") || 0) * 3),
          "height": (ele) => 16 + Math.min(28, (ele.data("degree") || 0) * 3),
        },
      },
      {
        selector: "edge",
        style: {
          "width": 1,
          "line-color": edgeColor,
          // bezier rather than haystack: haystack edges cannot carry a label,
          // and the relationship name is the point of the real-graph view
          "curve-style": "bezier",
          "opacity": 0.6,
          "target-arrow-shape": "triangle",
          "target-arrow-color": edgeColor,
          "arrow-scale": 0.6,
          "label": (ele) => ele.data("label") || "",
          "font-size": 7,
          "color": mutedColor,
          "text-rotation": "autorotate",
          "text-opacity": 0.75,
        },
      },
    ],
    layout: { name: "cose", animate: false, padding: 24 },
    boxSelectionEnabled: false,
  });

  // Re-fit on container resize (pane/window width changes, sidebar toggle).
  if (typeof ResizeObserver !== "undefined") {
    let raf = null;
    new ResizeObserver(() => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => { cy.resize(); cy.fit(undefined, 24); });
    }).observe(container);
  }

  if (graph.truncated) {
    const note = document.createElement("div");
    note.className = "answer-graph-note";
    note.textContent = graph.real
      ? `Showing ${graph.nodes.length} connected entities — the subgraph is larger.`
      : `Showing the first ${graph.nodes.length} entities — this result set has more.`;
    container.insertAdjacentElement("afterend", note);
  }
}

// Only a real chart from the agent's own Snowflake payload (vegaSpec/chart)
// is ever shown — no client-guessed "suggested" chart from the table — and
// it renders inline with the answer, always visible, no expand/collapse.
// Call once right after the answer HTML is mounted into the DOM.
function mountAnswerChart(msgEl, data) {
  if (!data.vegaSpec && !data.chart) return;
  const container = msgEl.querySelector(".answer-chart-wrap");
  if (!container || container.dataset.rendered) return;
  container.dataset.rendered = "1";

  function removeChartBlock(reason) {
    if (reason) console.warn("Chart render failed:", reason);
    const label = container.previousElementSibling;
    if (label && label.classList.contains("answer-chart-label")) label.remove();
    container.remove();
  }

  if (data.vegaSpec) {
    const vegaDiv = container.querySelector(".vega-wrap");
    // Vega-Lite's own "container" auto-size mode measures the element at
    // embed time via a ResizeObserver, which can catch it before the browser
    // has settled a real layout width (seen firsthand: the box read a solid
    // width moments later, but the chart itself had already locked in at 0).
    // Measuring the box ourselves — getBoundingClientRect() forces a
    // synchronous layout pass — and handing vega an explicit pixel size
    // sidesteps that race entirely.
    const rect = container.getBoundingClientRect();
    const spec = Object.assign({}, data.vegaSpec, {
      width: Math.round(rect.width) || 580,
      height: Math.round(rect.height) || 320,
      // Without this, "width"/"height" only bound the core plot area — the
      // legend, axis labels, and title (common on the agent's own specs,
      // e.g. a per-customer color legend) get added on top and can push the
      // whole SVG wider/taller than the box, spilling out of the card.
      // "fit" scales everything, including those, down to actually fit.
      autosize: { type: "fit", contains: "padding" },
    });
    vegaEmbed(vegaDiv, spec, {
      actions: false,
      theme: document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "excel",
      renderer: "svg",
    }).catch((err) => {
      if (data.chart) {
        vegaDiv.innerHTML = "<canvas></canvas>";
        try {
          renderAgentChart(vegaDiv.querySelector("canvas"), data.chart);
        } catch (chartErr) {
          removeChartBlock(chartErr);
        }
      } else {
        removeChartBlock(err);
      }
    });
  } else if (data.chart) {
    try {
      renderAgentChart(container.querySelector("canvas"), data.chart);
    } catch (err) {
      removeChartBlock(err);
    }
  }
}


// Markdown tables arrive as plain left-aligned cells, so a column of dollar
// amounts reads as ragged text. renderResultTable already right-aligns its
// numeric columns via .num (see th.num/td.num in style.css); this applies the
// same class to markdown tables after they are painted, judging a column by
// its cells rather than its header: every non-empty cell has to look like a
// figure ($1,234.50, -12%, 4,412, (900), 1.2M) before the column moves.
const NUMERIC_CELL_RE = /^[($\u2212-]*\s*\$?\s*\d[\d,\s]*(\.\d+)?\s*[%kKmMbB]?\)?$/;

function alignNumericTableCells(root) {
  if (!root) return;
  root.querySelectorAll("table").forEach((table) => {
    const bodyRows = [...table.querySelectorAll("tbody tr")];
    if (!bodyRows.length) return;
    const headCells = [...table.querySelectorAll("thead th")];
    const colCount = Math.max(headCells.length, ...bodyRows.map((r) => r.children.length));
    for (let i = 0; i < colCount; i++) {
      const cells = bodyRows.map((r) => r.children[i]).filter(Boolean);
      const filled = cells.filter((c) => c.textContent.trim() !== "");
      if (!filled.length) continue;
      if (!filled.every((c) => NUMERIC_CELL_RE.test(c.textContent.trim()))) continue;
      cells.forEach((c) => c.classList.add("num"));
      headCells[i]?.classList.add("num");
    }
  });
}




function makeThickDivider() {
  const hr = document.createElement("hr");
  hr.className = "answer-divider-thick";
  return hr;
}



// ---------------------------------------------------------------------------
// Planning card — live reasoning UI (Snowflake-style)
// ---------------------------------------------------------------------------
function createPlanningCard() {
  chatPanel.classList.remove("is-empty");
  const wrap = document.createElement("div");
  wrap.className = "planning-card";
  wrap.innerHTML = `
    <div class="planning-header">
      <span class="planning-icon"><span class="spinner-dots"><span></span></span></span>
      <span class="planning-title">Thinking</span>
      <button class="planning-toggle-btn" type="button">Show traces <span class="planning-chevron"></span></button>
    </div>
    <div class="planning-body" style="display:none"></div>`;
  chatWindow.appendChild(wrap);
  stickToBottom();

  const body    = wrap.querySelector(".planning-body");
  const btn     = wrap.querySelector(".planning-toggle-btn");
  const chevron = btn.querySelector(".planning-chevron");
  let expanded  = false; // reasoning trace stays collapsed by default — click to view

  btn.addEventListener("click", () => {
    expanded = !expanded;
    body.style.display = expanded ? "block" : "none";
    chevron.classList.toggle("up", expanded);
    btn.childNodes[0].textContent = expanded ? "Hide traces " : "Show traces ";
    if (expanded) revealAnswerEnd();
  });

  let currentThinkingPara = null;

  return {
    wrap,
    addThinkingDelta(text) {
      // Stream thinking content word by word
      if (!currentThinkingPara) {
        currentThinkingPara = document.createElement("p");
        currentThinkingPara.className = "plan-thinking-para";
        body.appendChild(currentThinkingPara);
      }

      // Check if we're starting a new paragraph (double newline in the stream)
      if (text.includes('\n\n')) {
        const parts = text.split('\n\n');
        currentThinkingPara.textContent += parts[0];
        // Start new paragraphs for remaining parts
        for (let i = 1; i < parts.length; i++) {
          if (parts[i].trim()) {
            currentThinkingPara = document.createElement("p");
            currentThinkingPara.className = "plan-thinking-para";
            currentThinkingPara.textContent = parts[i];
            body.appendChild(currentThinkingPara);
          }
        }
      } else {
        currentThinkingPara.textContent += text;
      }
    },
    // Renders one already-complete reasoning paragraph in one shot — used to
    // replay a saved Recents conversation, as opposed to addThinkingDelta's
    // word-by-word live streaming.
    addThinkingParagraph(text) {
      const p = document.createElement("p");
      p.className = "plan-thinking-para";
      p.textContent = text;
      body.appendChild(p);
    },
    resetThinkingPara() {
      currentThinkingPara = null;
    },
    complete() {
      wrap.querySelector(".planning-icon").innerHTML = `<span class="plan-check">&#10003;</span>`;
      wrap.querySelector(".planning-title").textContent = "Thinking";
      btn.childNodes[0].textContent = "Show traces ";
      body.style.display = "none";
      expanded = false;
      chevron.classList.remove("up");
    },
    remove() { wrap.remove(); },
  };
}

async function askQuestion(question) {
  if (isProcessing) return;
  clearFollowupSuggestions();

  if (isGreetingOnly(question)) {
    stickToBottomEnabled = true;   // the user just sent this — go to it
  const greetingUserEl = addMessage("user", escapeHtml(question));
    addUserRegenerateButton(greetingUserEl, question);
    addMessage("assistant", `<div class="msg-text">${escapeHtml(localGreetingReply())}</div>`);
    chatInput.value = "";
    autoResizeTextarea();
    historyNavIndex = -1;
    draftBeforeNav = "";
    return; // no server round-trip, nothing to add to Recents
  }

  stickToBottomEnabled = true;   // the user just sent this — go to it
  const userEl = addMessage("user", escapeHtml(question));
  addUserRegenerateButton(userEl, question);
  // Send more turns than the server will use — app.py budgets them down by
  // character count (HISTORY_TURNS / HISTORY_TOTAL_CHARS), so the trimming
  // decision lives in one place instead of being split across the wire.
  const historyForRequest = currentThreadHistory.slice(-8).map((h) => ({ question: h.question, answer: h.answer }));
  const historyEntry = addToHistory(question);
  chatInput.value = "";
  autoResizeTextarea();
  historyNavIndex = -1;
  draftBeforeNav = "";
  setProcessing(true);
  const controller = new AbortController();
  currentAbortController = controller;

  // The one assistant message card holding the graph answer.
  // fixed order up front so each section lands in the right place no matter
  // which of the parallel calls below finishes (or starts streaming text)
  // first — only created once real content is about to appear (right after
  // the planning card), by whichever section gets there first.
  let agentEl = null;
  function ensureAgentEl() {
    if (!agentEl) {
      agentEl = addMessage("assistant", `
        <div class="answer-chart-label">KG answer</div>
        <div class="msg-text markdown-body"></div>
        <div class="agent-extras"></div>`);
    }
    return agentEl;
  }



  // ── Streaming agent call with live planning card ──────────────────────
  // Resolves as soon as the 'done' event arrives — same moment as before —
  // but the underlying read loop keeps draining afterward (see below) to
  // keep the stream open past 'done', since relevance judging and history
  // persistence happen server-side AFTER 'done' is sent so they never hold up
  // the table/chart/actions the rest of the page is waiting on.
  function streamAgent() {
    const planCard = createPlanningCard();
    const typewriter = createTypewriter(
      () => ensureAgentEl().querySelector(".markdown-body"),
      { onDone: () => attachClarifyingOptions(ensureAgentEl()) },
    );

    let settled = false;
    let sawThinking = false;
    let resolveEarly, rejectEarly;
    const earlyPromise = new Promise((resolve, reject) => { resolveEarly = resolve; rejectEarly = reject; });
    const settleOnce = (result) => { if (!settled) { settled = true; resolveEarly(result); } };

    (async () => {
      try {
        const resp = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question, history: historyForRequest, conversation_id: currentConversationId,
            concise: conciseToggle?.checked || false,
          }),
          signal: controller.signal,
        });
        if (!resp.ok) {
          planCard.remove();
          settleOnce({ error: "Something went wrong while processing your question. Please try again." });
          return;
        }

        const steps = [];
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        let curEvent = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          let idx;
          while ((idx = buf.indexOf("\n\n")) !== -1) {
            const msg = buf.slice(0, idx);
            buf = buf.slice(idx + 2);
            for (const line of msg.split("\n")) {
              if (line.startsWith("event:")) {
                curEvent = line.slice(6).trim();
              } else if (line.startsWith("data:")) {
                let payload;
                try { payload = JSON.parse(line.slice(5).trim()); }
                catch { continue; }
                if (curEvent === "thinking_delta" && payload.text) {
                  // Stream thinking content in real-time
                  sawThinking = true;
                  planCard.addThinkingDelta(payload.text);
                } else if (curEvent === "text_delta" && payload.text) {
                  // Feed the answer text into the typewriter as it's generated —
                  // it paces the reveal itself, independent of how bursty these
                  // deltas actually arrive.
                  typewriter.push(payload.text);
                } else if (curEvent === "text_reset") {
                  typewriter.reset();
                } else if (curEvent === "done") {
                  // Cache hit: the answer came back whole, with its saved
                  // reasoning steps but no live thinking stream to fill the
                  // card from.
                  if (!sawThinking) {
                    (payload.reasoningSteps || []).forEach((step) => planCard.addThinkingParagraph(step));
                  }
                  planCard.resetThinkingPara();
                  planCard.complete();
                  typewriter.finish(payload.answer || "");
                  settleOnce({ data: payload, steps });
                } else if (curEvent === "error") {
                  planCard.remove();
                  settleOnce({ error: payload.error || "Unknown error" });
                  return;
                }
              }
            }
          }
        }
        // Only a stream that ended *without* ever sending 'done' is a failure
        // worth clearing the card for. Ending after 'done' is the normal close
        // — and the completed card is the answer's thinking trace, which has to
        // survive it. It used to be removed either way, so a cached answer
        // (where 'done' and the close arrive together) flashed the card and
        // lost the trace.
        if (!settled) {
          planCard.remove();
          settleOnce({ error: "Stream ended unexpectedly" });
        }
      } catch (err) {
        if (!settled) planCard.remove();
        if (settled) return; // error happened during the post-done relevance drain — nothing more to signal
        rejectEarly(err);
      }
    })();

    return earlyPromise;
  }



  try {
    const agentResult = await streamAgent();

    if (agentResult.error) {
      const el = ensureAgentEl();
      const content = el.querySelector(".msg-content");
      if (content) content.innerHTML = `<div class="msg-text">${escapeHtml(agentResult.error)}</div>`;
      return;
    }

    const agentResp = agentResult.data;
    historyEntry.answer = agentResp.answer;
    historyEntry.id = agentResp.interaction_id || historyEntry.id;
    historyEntry.hasSql = Boolean(agentResp.sql);
    historyEntry.sql = agentResp.sql || null;
    historyEntry.columns = agentResp.columns || null;
    historyEntry.rows = agentResp.rows || null;
    historyEntry.tableTitle = agentResp.tableTitle || null;
    historyEntry.chart = agentResp.chart || null;
    historyEntry.vegaSpec = agentResp.vegaSpec || null;
    historyEntry.usage = agentResp.usage || null;
    historyEntry.elapsed = agentResp.elapsed != null ? agentResp.elapsed : null;
    historyEntry.relevancePercent = null;
    historyEntry.steps = agentResp.reasoningSteps || [];
    renderHistorySidebar();

    // ── Agent answer — the text is fully painted by now (finish() ran when
    // the 'done' frame arrived); append the extras that only ever arrive at
    // the end (chart/table/SQL dropdown/action row/usage stats) without
    // touching the markdown text itself.
    const agentEl = ensureAgentEl();
    const extras = agentEl.querySelector(".agent-extras");
    if (extras) extras.innerHTML = buildAnswerExtrasHtml(agentResp, true);
    attachCollapsibles(agentEl, agentResp);
    mountAnswerChart(agentEl, agentResp);
    attachActionRow(agentEl, {
      interactionId: agentResp.interaction_id,
      question,
      answer: agentResp.answer,
      isAgent: true,
      columns: agentResp.columns,
      rows: agentResp.rows,
    });
    renderFollowupSuggestions(agentResp.suggestions);
    // The blocks above were appended after the last streamed paint, so the
    // bottom of the answer is off-screen until the view catches up.
    revealAnswerEnd();

  } catch (err) {
    // Streaming may already have created the shared card and started
    // filling it in before the abort/error happened — reuse it instead of
    // leaving a half-streamed answer sitting above a separate error bubble.
    const el = ensureAgentEl();
    const content = el.querySelector(".msg-content");
    const message = err.name === "AbortError"
      ? "Stopped."
      : "Something went wrong while processing your question. Please try again.";
    if (content) content.innerHTML = `<div class="msg-text">${escapeHtml(message)}</div>`;
  } finally {
    setProcessing(false);
    currentAbortController = null;
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  if (isProcessing) {
    if (currentAbortController) currentAbortController.abort();
    return;
  }
  const q = chatInput.value.trim();
  if (q) askQuestion(q);
});

const downloadConversationBtn = document.getElementById("download-conversation-btn");
downloadConversationBtn?.addEventListener("click", () => downloadConversationAsPdf());

document.querySelectorAll(".start-suggestion").forEach((btn) => {
  btn.addEventListener("click", () => askQuestion(btn.textContent.trim()));
});

// ---------------------------------------------------------------------------
// Landing-page dashboard metrics — one overall summary row (all sites,
// latest snapshot), refreshed server-side once a day. Just reads whatever
// the server currently has cached; no polling — a fresh page load is what
// picks up that day's numbers.
// ---------------------------------------------------------------------------
function setMetric(id, text, cls) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = text;
  el.classList.remove("loading", "error");
  if (cls) el.classList.add(cls);
}

function setMetricsFooter(text) {
  const el = document.getElementById("metrics-footer");
  if (el) el.textContent = text || "";
}

// The server sends fetched_at in UTC (ISO with offset) — Date + toLocaleString
// below convert it to whatever timezone the viewer's browser is in.
function formatLocalTimestamp(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString([], {
    year: "numeric", month: "short", day: "numeric",
    hour: "numeric", minute: "2-digit",
    timeZoneName: "short",
  });
}

const DASHBOARD_METRIC_IDS = [
  "metric-inventory-value", "metric-median-doi", "metric-open-po-value",
  "metric-delayed-shipments", "metric-eol-parts", "metric-customers",
];


function renderDashboardMetrics(data) {
  if (data.loading) {
    DASHBOARD_METRIC_IDS.forEach((id) => setMetric(id, "Loading…", "loading"));
    setMetricsFooter("");
    return;
  }
  if (data.error && data.inventory_value_usd == null) {
    DASHBOARD_METRIC_IDS.forEach((id) => setMetric(id, "Unavailable", "error"));
    setMetricsFooter("");
    return;
  }
  setMetric("metric-inventory-value", data.inventory_value_usd != null ? formatUsdCompact(data.inventory_value_usd) : "—");
  // A day count, not money — rounded to whole days, which is as precise as
  // a median over a 25k-row snapshot is worth reporting.
  setMetric("metric-median-doi", data.median_doi != null ? `${Math.round(data.median_doi).toLocaleString()} d` : "—");
  setMetric("metric-open-po-value", data.open_po_value_usd != null ? formatUsdCompact(data.open_po_value_usd) : "—");
  setMetric("metric-delayed-shipments", data.delayed_shipments != null ? Math.round(data.delayed_shipments).toLocaleString() : "—");
  setMetric("metric-eol-parts", data.eol_parts != null ? Math.round(data.eol_parts).toLocaleString() : "—");
  setMetric("metric-customers", data.num_customers != null ? Math.round(data.num_customers).toLocaleString() : "—");
  setMetricsFooter(data.fetched_at ? `* As of ${formatLocalTimestamp(data.fetched_at)}` : "");
}

async function loadDashboardMetrics() {
  try {
    renderDashboardMetrics(await fetch("/api/dashboard-metrics").then((r) => r.json()));
  } catch {
    renderDashboardMetrics({ error: "Unavailable" });
  }
}
loadDashboardMetrics();

const metricsRefreshBtn = document.getElementById("metrics-refresh-btn");
metricsRefreshBtn?.addEventListener("click", async () => {
  if (metricsRefreshBtn.disabled) return;
  metricsRefreshBtn.disabled = true;
  metricsRefreshBtn.classList.add("spinning");
  try {
    const resp = await fetch("/api/dashboard-metrics/refresh", { method: "POST" });
    renderDashboardMetrics(await resp.json());
  } catch {
    renderDashboardMetrics({ error: "Unavailable" });
  } finally {
    metricsRefreshBtn.disabled = false;
    metricsRefreshBtn.classList.remove("spinning");
  }
});

// ---------------------------------------------------------------------------
// Multi-line input: auto-resize + Enter/Shift+Enter + arrow-key history recall
// ---------------------------------------------------------------------------
const MAX_TEXTAREA_HEIGHT = 200;

// ---------------------------------------------------------------------------
// Dashboard shade: click the grab bar to collapse or open the metrics row, or
// drag it down/up to do the same by hand. Which state it is in survives a
// reload, so someone who works with it shut is not handed it back every time.
// ---------------------------------------------------------------------------
const dashboardWrap = document.getElementById("metrics-dashboard-wrap");
const dashboardBody = document.getElementById("dashboard-body");
const dashboardHandle = document.getElementById("dashboard-handle");
const dashboardHandleLabel = document.getElementById("dashboard-handle-label");

if (dashboardWrap && dashboardBody && dashboardHandle) {
  const naturalHeight = () => {
    // Measured with any cap lifted, so a drag that started from a collapsed
    // shade still knows how far down it can go.
    const prev = dashboardBody.style.maxHeight;
    dashboardBody.style.maxHeight = "none";
    const h = dashboardBody.scrollHeight;
    dashboardBody.style.maxHeight = prev;
    return h;
  };

  // Open on the landing page, collapsed once a conversation is on screen —
  // the metrics are an opening summary, not something to keep giving up room
  // to while reading answers. Still toggleable by hand at any time; the view
  // only takes over again on the next switch between landing and conversation.
  const onLandingPage = () => chatPanel.classList.contains("is-empty");
  let collapsed = !onLandingPage();

  function setCollapsed(next) {
    collapsed = next;
    dashboardWrap.classList.toggle("is-collapsed", collapsed);
    dashboardBody.style.maxHeight = collapsed ? "0px" : naturalHeight() + "px";
    dashboardHandle.setAttribute("aria-expanded", String(!collapsed));
    if (dashboardHandleLabel) dashboardHandleLabel.textContent = collapsed ? "Show dashboard" : "Hide dashboard";
  }

  // Once open, drop the cap so later content changes cannot be clipped by a
  // height measured before they happened.
  dashboardBody.addEventListener("transitionend", (e) => {
    if (e.propertyName === "max-height" && !collapsed) dashboardBody.style.maxHeight = "none";
  });

  setCollapsed(collapsed);
  // No animation to wait on at load, so lift the cap straight away.
  if (!collapsed) dashboardBody.style.maxHeight = "none";

  // Four separate places add or remove is-empty (first message, replaying a
  // conversation, planning card, New chat); watching the class covers them all
  // without each having to remember to call this.
  let wasLanding = onLandingPage();
  new MutationObserver(() => {
    const landing = onLandingPage();
    if (landing === wasLanding) return;
    wasLanding = landing;
    setCollapsed(!landing);
  }).observe(chatPanel, { attributes: true, attributeFilter: ["class"] });

  let dragStartY = null;
  let dragStartHeight = 0;
  let dragged = false;

  dashboardHandle.addEventListener("pointerdown", (e) => {
    dragStartY = e.clientY;
    dragStartHeight = dashboardBody.getBoundingClientRect().height;
    dragged = false;
    dashboardBody.style.transition = "none";
    dashboardBody.style.maxHeight = dragStartHeight + "px";
    dashboardWrap.classList.remove("is-collapsed");
    dashboardHandle.setPointerCapture(e.pointerId);
  });

  dashboardHandle.addEventListener("pointermove", (e) => {
    if (dragStartY === null) return;
    const dy = e.clientY - dragStartY;
    if (Math.abs(dy) > 3) dragged = true;
    const max = naturalHeight();
    dashboardBody.style.maxHeight = Math.max(0, Math.min(max, dragStartHeight + dy)) + "px";
  });

  function endDrag(e) {
    if (dragStartY === null) return;
    const height = dashboardBody.getBoundingClientRect().height;
    dragStartY = null;
    dashboardBody.style.transition = "";
    if (dashboardHandle.hasPointerCapture?.(e.pointerId)) dashboardHandle.releasePointerCapture(e.pointerId);
    // A drag settles to whichever end it finished nearer; a click (no real
    // movement) just toggles.
    setCollapsed(dragged ? height < naturalHeight() / 2 : !collapsed);
  }
  dashboardHandle.addEventListener("pointerup", endDrag);
  dashboardHandle.addEventListener("pointercancel", endDrag);

  dashboardHandle.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setCollapsed(!collapsed); }
    else if (e.key === "ArrowUp" && !collapsed) { e.preventDefault(); setCollapsed(true); }
    else if (e.key === "ArrowDown" && collapsed) { e.preventDefault(); setCollapsed(false); }
  });

  // The metric values arrive after this runs, and a refresh can change how
  // tall the row is; re-measure so the open height keeps matching the content.
  window.addEventListener("resize", () => { if (!collapsed) dashboardBody.style.maxHeight = "none"; });
}

function autoResizeTextarea() {
  chatInput.style.height = "auto";
  chatInput.style.height = Math.min(chatInput.scrollHeight, MAX_TEXTAREA_HEIGHT) + "px";
}
chatInput.addEventListener("input", () => {
  autoResizeTextarea();
  historyNavIndex = -1;
});

let historyNavIndex = -1; // -1 = not navigating (showing the in-progress draft)
let draftBeforeNav = "";

chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    chatForm.requestSubmit();
    return;
  }

  if (e.key === "ArrowUp") {
    if (chatInput.selectionStart !== 0 || chatInput.selectionEnd !== 0) return;
    const entries = sessionHistory.flatMap((c) => c.messages).reverse(); // most-recent-first
    if (!entries.length || historyNavIndex >= entries.length - 1) return;
    e.preventDefault();
    if (historyNavIndex === -1) draftBeforeNav = chatInput.value;
    historyNavIndex++;
    chatInput.value = entries[historyNavIndex].question;
    autoResizeTextarea();
    chatInput.setSelectionRange(0, 0);
  } else if (e.key === "ArrowDown") {
    const len = chatInput.value.length;
    if (chatInput.selectionStart !== len || chatInput.selectionEnd !== len) return;
    if (historyNavIndex === -1) return;
    e.preventDefault();
    historyNavIndex--;
    const entries = sessionHistory.flatMap((c) => c.messages).reverse();
    chatInput.value = historyNavIndex === -1 ? draftBeforeNav : entries[historyNavIndex].question;
    autoResizeTextarea();
    const newLen = chatInput.value.length;
    chatInput.setSelectionRange(newLen, newLen);
  }
});

// ---------------------------------------------------------------------------
// New chat
// ---------------------------------------------------------------------------
function startNewChat() {
  if (isProcessing && currentAbortController) currentAbortController.abort();
  currentConversationId = crypto.randomUUID(); // start a genuinely new conversation
  currentThreadHistory = []; // reset conversational context only — Recents list (sessionHistory) stays
  historyNavIndex = -1;
  draftBeforeNav = "";
  clearFollowupSuggestions();
  chatWindow.querySelectorAll(".msg, .planning-card").forEach((el) => el.remove());
  chatPanel.classList.add("is-empty");
  chatInput.value = "";
  autoResizeTextarea();
  if (historySearch) historySearch.value = "";
  renderHistorySidebar();
}
newChatBtn?.addEventListener("click", startNewChat);

// ---------------------------------------------------------------------------
// Global keyboard shortcuts
// ---------------------------------------------------------------------------
document.addEventListener("keydown", (e) => {
  const mod = e.ctrlKey || e.metaKey;
  if (mod && e.key === "\\") {
    e.preventDefault();
    toggleSidebar();
  } else if (mod && e.key.toLowerCase() === "k") {
    e.preventDefault();
    startNewChat();
  } else if (e.key === "Escape" && isProcessing && currentAbortController) {
    currentAbortController.abort();
  }
});

// ---------------------------------------------------------------------------
// Toast (brief transient message, e.g. after Logout)
// ---------------------------------------------------------------------------
let toastTimer = null;
function showToast(message) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.hidden = true; }, 2500);
}

// ---------------------------------------------------------------------------
// User menu (sidebar avatar) — Total usage / Logout
// ---------------------------------------------------------------------------
const userMenuBtn = document.getElementById("user-menu-btn");
const userMenu = document.getElementById("user-menu");

function closeUserMenu() {
  if (!userMenu || userMenu.hidden) return;
  userMenu.hidden = true;
  userMenuBtn?.setAttribute("aria-expanded", "false");
}
function toggleUserMenu() {
  if (!userMenu) return;
  const opening = userMenu.hidden;
  userMenu.hidden = !opening;
  userMenuBtn?.setAttribute("aria-expanded", String(opening));
}
userMenuBtn?.addEventListener("click", (e) => {
  e.stopPropagation();
  toggleUserMenu();
});
document.addEventListener("click", (e) => {
  if (!userMenu || userMenu.hidden) return;
  if (!userMenu.contains(e.target) && e.target !== userMenuBtn && !userMenuBtn?.contains(e.target)) {
    closeUserMenu();
  }
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && userMenu && !userMenu.hidden) closeUserMenu();
});

document.getElementById("logout-menu-item")?.addEventListener("click", () => {
  closeUserMenu();
  showToast("Logged out");
});

// ---------------------------------------------------------------------------
// Total usage modal — date / query / tokens / cost for every agent call ever
// made by this user (fetched fresh from the append-only interaction log, not
// from the deduped Recents list, so repeated questions aren't undercounted).
// ---------------------------------------------------------------------------
const usageModalOverlay = document.getElementById("usage-modal-overlay");

async function openUsageModal() {
  const summary = document.getElementById("usage-summary");
  const tbody   = document.getElementById("usage-table-body");
  if (!usageModalOverlay || !summary || !tbody) return;

  usageModalOverlay.hidden = false;
  summary.textContent = "Loading…";
  tbody.innerHTML = "";

  let rows = [];
  try {
    const data = await fetch("/api/usage").then((r) => r.json());
    rows = (data.usage || []).slice().reverse(); // most-recent-first
  } catch {
    summary.textContent = "Failed to load usage.";
    return;
  }

  let totalTokens = 0, totalCost = 0;
  tbody.innerHTML = rows.map((h) => {
    totalTokens += h.total_tokens || 0;
    totalCost   += h.cost || 0;
    return `<tr>
      <td>${escapeHtml(formatHistoryTime(h.timestamp) || "—")}</td>
      <td>${escapeHtml(h.question)}</td>
      <td class="num">${(h.total_tokens || 0).toLocaleString()}</td>
      <td class="num">$${(h.cost || 0).toFixed(5)}</td>
    </tr>`;
  }).join("") || `<tr><td colspan="4" class="muted">No usage yet.</td></tr>`;

  summary.textContent = `${rows.length} call${rows.length === 1 ? "" : "s"} · ${totalTokens.toLocaleString()} tokens · $${totalCost.toFixed(5)} total`;
}
function closeUsageModal() {
  if (usageModalOverlay) usageModalOverlay.hidden = true;
}

document.getElementById("usage-menu-item")?.addEventListener("click", () => {
  closeUserMenu();
  openUsageModal();
});
document.getElementById("usage-modal-close")?.addEventListener("click", closeUsageModal);
usageModalOverlay?.addEventListener("click", (e) => {
  if (e.target === usageModalOverlay) closeUsageModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && usageModalOverlay && !usageModalOverlay.hidden) closeUsageModal();
});

