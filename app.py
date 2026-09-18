"""
app.py — "Supply Chain KG": Supply-Chain Knowledge-Graph Chatbot (Flask)
=========================================================================
A natural-language chatbot over the supply-chain / E&O knowledge graph held
in Snowflake. Each question is handed to a Snowflake Cortex agent via

    POST https://<account>.snowflakecomputing.com/api/v2/cortex/agent:run

with the model, instructions and tools defined inline in this file and sent on
every request, so there is no stored AGENT object to deploy. The answer is streamed back with a table and, where useful, a
chart. The landing-page tiles and the graph view are read straight from
Snowflake with ordinary SQL.

Routes:
  GET  /                 — single-page chat app
  POST /api/chat         — question -> Cortex agent -> answer + table + chart
  POST /api/subgraph     — entities in an answer -> real KG nodes/edges

Snowflake is the ONLY data connection. There is no Neo4j, Neptune or AWS
backend any more — put the credentials in a .env file next to app.py.

Run:
    pip install -r requirements.txt
    python app.py
"""

import getpass
import json
import os
import random
import re
import threading
import time
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import requests
import snowflake.connector
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

# ── Snowflake — the only data connection ────────────────────────────────────
# Auth is a programmatic access token (PAT): Snowflake's own recommendation
# for headless service accounts, and the only mechanism that needs no key
# file or browser round-trip on the server. The token is read from the
# environment and never hard-coded here, so rotating it is a .env edit
# rather than a code change.
SNOWFLAKE_ACCOUNT   = os.environ.get("SNOWFLAKE_ACCOUNT")
SNOWFLAKE_USER      = os.environ.get("SNOWFLAKE_USER")
SNOWFLAKE_TOKEN     = os.environ.get("SNOWFLAKE_PAT")
SNOWFLAKE_ROLE      = os.environ.get("SNOWFLAKE_ROLE", "SUPPLYCHAIN")
SNOWFLAKE_WAREHOUSE = os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
SNOWFLAKE_DATABASE  = os.environ.get("SNOWFLAKE_DATABASE", "SCS")
SNOWFLAKE_SCHEMA    = os.environ.get("SNOWFLAKE_SCHEMA", "INVENTORY")

# Cortex Agents REST endpoint. The tools are defined inline in this file and
# sent with every request (see AGENT_TOOLS), so there is no stored AGENT
# object to create or keep in sync — the account host is all that's needed.
SNOWFLAKE_HOST = os.environ.get(
    "SNOWFLAKE_HOST", f"{(SNOWFLAKE_ACCOUNT or '').upper()}.snowflakecomputing.com")

# The two Cortex resources the agent's tools are pointed at.
SEMANTIC_VIEW  = os.environ.get("SEMANTIC_VIEW", "SCS.SEMANTIC.SV_SUPPLY_CHAIN_KG")
SEARCH_SERVICE = os.environ.get("SEARCH_SERVICE", "SCS.SEMANTIC.SCM_DOCUMENT_SEARCH")

# Schema holding the knowledge-graph node/edge tables the graph view reads.
KG_SCHEMA = os.environ.get("KG_SCHEMA", "SCS.KG")

SQL_TIMEOUT = int(os.environ.get("SNOWFLAKE_QUERY_TIMEOUT", "120"))
# agent:run is a synchronous call that plans, runs tools and writes an answer
# in one request — measured at ~20-90s, so it needs a far longer leash than an
# ordinary query.
AGENT_TIMEOUT = int(os.environ.get("CORTEX_AGENT_TIMEOUT", "300"))
MAX_ROWS      = int(os.environ.get("MAX_ROWS", "200"))

if not (SNOWFLAKE_ACCOUNT and SNOWFLAKE_USER and SNOWFLAKE_TOKEN):
    raise RuntimeError(
        "SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER and SNOWFLAKE_PAT must be set — "
        "create a .env next to app.py"
    )

CHATBOT_NAME = "Supply Chain KG"

# ── Azure OpenAI — optional: follow-up suggestions and the relevance judge ──
# Neither is on the answer path any more (the Cortex agent writes the answer
# itself), so the app runs fine with these unset — the features just switch
# themselves off rather than failing the request.
AZURE_OPENAI_API_KEY  = os.getenv("AZURE_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_OPENAI_VERSION  = os.getenv("AZURE_API_VERSION")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_DEPLOYMENT")









# renderer to the frontend, translate the spec into the minimal shape the
# app's existing Chart.js setup needs — this is a best-effort read of the
# handful of fields the agent actually emits (mark type, x/y field+title,
# an optional color/series field, and a "$" axis format hint).
# The agent's own queries frequently key trends off a WEEK_KEY/week-number
# column (e.g. "2629") instead of a real calendar date — that column must
# never reach the UI. Wherever it shows up as the chart's x-axis or a table
# column, swap it for (or drop it in favor of) an actual date field.
_WEEK_COLUMN_NAMES = {"week_key", "week", "week_num", "week_number", "weeknum"}


def _is_week_column(name: str) -> bool:
    return bool(name) and name.strip().lower() in _WEEK_COLUMN_NAMES


def _find_date_field(values: list, exclude: str = None):
    if not values:
        return None
    for key in values[0].keys():
        if key != exclude and "date" in key.lower():
            return key
    return None


def _strip_week_columns(columns: list, rows: list):
    keep = [i for i, c in enumerate(columns) if not _is_week_column(c)]
    if len(keep) == len(columns):
        return columns, rows
    return [columns[i] for i in keep], [[row[i] for i in keep] for row in rows]


# Measures the answers must not surface. The agent is told not to name these
# in prose (see ANSWER_RESPONSE_INSTRUCTION), and it obeys — but a table's
# columns are SQL aliases from the query it ran, and a chart's labels come
# from the spec it emitted, so neither is governed by an instruction about
# wording. They are filtered here instead, where the data actually reaches
# the page.
_SUPPRESSED_MEASURE_RE = re.compile(
    r"hub[\s_-]*score|authority[\s_-]*score|(?<![a-z])hits(?![a-z])", re.I)


def _strip_suppressed_columns(columns: list, rows: list):
    """Drop columns naming a measure the UI must not show."""
    if not columns:
        return columns, rows
    keep = [i for i, c in enumerate(columns)
            if not _SUPPRESSED_MEASURE_RE.search(str(c or ""))]
    if len(keep) == len(columns):
        return columns, rows
    if not keep:
        # Nothing left worth rendering — the whole table was the banned measure.
        return None, None
    return [columns[i] for i in keep], [[row[i] for i in keep] for row in rows]


def _chart_mentions_suppressed(spec) -> bool:
    """True when a chart spec names a suppressed measure anywhere.

    Checked against the serialized spec rather than specific encoding fields
    because the name can sit in a field reference, an axis title, a legend
    label or an inline data record, and missing any one of them puts it back
    on screen.
    """
    try:
        return bool(_SUPPRESSED_MEASURE_RE.search(json.dumps(spec)))
    except (TypeError, ValueError):
        return False


_MD_TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
_MD_TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$")


def _extract_markdown_table(text):
    """The agent doesn't always emit a separate structured "table" content
    block alongside its final answer — sometimes it just writes a markdown
    table straight into the answer text (confirmed empirically: ~1 in 4
    stored answers have a markdown table in their text with no structured
    columns/rows at all). When that happens, the Database output and Graph
    view sections have nothing to show even though a table is sitting right
    there in the rendered answer. This parses the FIRST such table out of the
    text as a fallback, so those sections still populate."""
    if not text:
        return None, None
    lines = text.splitlines()
    for i in range(len(lines) - 1):
        header_m = _MD_TABLE_ROW_RE.match(lines[i])
        if not header_m:
            continue
        sep_m = _MD_TABLE_SEP_RE.match(lines[i + 1])
        if not (sep_m and "-" in lines[i + 1]):
            continue
        columns = [c.strip().strip("*") for c in header_m.group(1).split("|")]
        rows = []
        for line in lines[i + 2:]:
            row_m = _MD_TABLE_ROW_RE.match(line)
            if not row_m:
                break
            cells = [c.strip().strip("*") for c in row_m.group(1).split("|")]
            if len(cells) == len(columns):
                rows.append(cells)
        if rows:
            return columns, rows
    return None, None



# A larger pool than what's actually shown — the landing page randomly
# samples a handful of these (and shuffles their order) on every page load,
# so repeat visits don't always see the same five chips in the same spots.
SAMPLE_QUESTIONS = [
    "Which are the most critical suppliers in the supply chain?",
    "Which supplier sites are single points of failure?",
    "Give me a summary of the knowledge graph",
    "Which parts have the most alternate approved sources?",
    "Which parts are single-sourced, and from whom?",
    "Which plants ship to the most customers?",
    "Which suppliers are the biggest bottlenecks in the network?",
    "How are the entities split across the network's separate components?",
    "Which shipping lanes connect the most ports?",
    "What do the supplier scorecards say about quality issues?",
    "What do the non-conformance reports flag most often?",
    "Which contracts mention quality guarantees or penalties?",
    "Which commodities have the widest supplier base?",
    "Which countries do the most critical suppliers sit in?",
]
SAMPLE_QUESTIONS_SHOWN = 5

# ── Landing-page dashboard metrics ──────────────────────────────────────────
# One overall summary row (latest snapshot) shown at the top of the landing
# page. Read with plain SQL rather than through the agent: these six numbers
# are fixed, the query never varies, and a deterministic statement is both
# far cheaper and immune to the agent re-aliasing its output columns between
# calls. See DASHBOARD_SQL for what each tile actually measures.
_dashboard_metrics_lock = threading.Lock()
_dashboard_metrics_cache = {"data": None, "fetched_at": None, "error": None}

# Persists the last-fetched dashboard metrics across restarts, so the tiles
# show the last known values immediately
# on startup instead of sitting on "Loading…" until someone clicks refresh —
# since refreshing is purely user-triggered now, nothing else will populate
# them otherwise.
DASHBOARD_METRICS_DATA_FILE = Path(__file__).parent / "dashboard_metrics_data.json"


def _load_saved_dashboard_metrics():
    try:
        saved = json.loads(DASHBOARD_METRICS_DATA_FILE.read_text())
        return saved.get("data"), saved.get("fetched_at")
    except (OSError, ValueError):
        return None, None


def _save_dashboard_metrics(data, fetched_at):
    tmp = DASHBOARD_METRICS_DATA_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"data": data, "fetched_at": fetched_at}))
    tmp.replace(DASHBOARD_METRICS_DATA_FILE)


def _find_metric_column(columns, include, exclude=()):
    for i, col in enumerate(columns or []):
        upper = col.upper()
        if include in upper and not any(x in upper for x in exclude):
            return i
    return None








# No background thread anymore — the tiles only ever change when the user
# clicks the refresh button. On startup, load whatever was last saved so the
# tiles show real numbers immediately instead of sitting on "Loading…" with
# nothing to populate them until that click happens.
_saved_metrics_data, _saved_metrics_fetched_at = _load_saved_dashboard_metrics()
if _saved_metrics_data is not None:
    _dashboard_metrics_cache["data"] = _saved_metrics_data
    _dashboard_metrics_cache["fetched_at"] = _saved_metrics_fetched_at


# Terms a follow-up suggestion must not contain. Deliberately empty: the
# earlier list ("pagerank", "louvain", "supplier") was written for the E&O
# graph, where those were off-topic. On this supply-chain KG they are the
# subject matter, and the filter silently discarded most suggestions.
SUPPRESSED_SUGGESTION_TERMS = ()

# stalls on a clarifying "which site?" question when the user's own question
# never named one.
DEFAULT_ALL_SITES_INSTRUCTION = (
    " If the user's question does not mention a specific site, use all sites combined "
    "instead of asking which site they mean."
)

# Sent as the agent's own `instructions.response` on every request — the
# standing description of who it is and how it writes, as opposed to
# ANSWER_STYLE_INSTRUCTION below, which rides along with each question.
ANSWER_RESPONSE_INSTRUCTION = (
    "You are a supply-chain analyst assistant answering questions about the Asterion "
    "Devices supply chain. All data is synthetic. Answer with findings only — no "
    "narration of your own steps. Present rankings, breakdowns and trends as a "
    "markdown table with a header row, a separator row, and no blank lines between "
    "rows. Express monetary figures in USD. Refer to time periods by calendar date, "
    "never by week number. Never write the words hub score, authority score or HITS in "
    "your answer, its tables or its chart labels. This holds even when the question "
    "itself uses those words: do not mirror the term back. Rank by the measure if it "
    "is the right one, but name it for what it shows — network reach, or breadth of "
    "supply across the network — and report a column a reader recognises."
)

ANSWER_STYLE_INSTRUCTION = (
    " (Most important rule, above everything else below: your final answer text must contain ONLY "
    "the findings and conclusions themselves — zero thinking traces, zero process narration, zero "
    "meta-commentary about what you did or are about to do. Every one of your own tool-call turns "
    "and internal reasoning stays there and never gets copied, paraphrased, or summarized into the "
    "final answer text. Banned patterns include (this list is illustrative, not exhaustive — reject "
    "the whole category, not just these exact phrases): 'Now I'll query...', 'Let me check/look "
    "at/query/verify/fix...', 'The query returned 0 rows', 'I found that...', 'Looking at the "
    "data...', 'Based on my analysis...', 'First, I need to...', 'Perfect! The customer is...', "
    "'Great! Now I have the data', 'Let me also load/fix the chart...', 'Now let me create a "
    "comprehensive summary...', or any sentence describing your own steps, tools, queries, or "
    "process at all. Before you finalize, reread every sentence you're about to output and delete "
    "any that describes what you (the assistant) are doing, checking, or about to do, rather than "
    "stating a business fact directly. The final answer must read as a single, clean, "
    "already-finished write-up — as if you had known the results from the start and were never "
    "narrating your own work.\n\n"
    "In your answer, use plain business language — explain what a graph measure means in "
    "business terms when you use one (e.g. PageRank as overall importance in the network, "
    "betweenness as bottleneck risk) rather than leaving a bare score to speak for itself. "
    "Never write the words hub score, authority score or HITS anywhere in the answer, its "
    "tables or its chart labels — not even if the question uses those words, in which case "
    "answer it without repeating the term. Rank by the measure where it is the right one, "
    "but call it network reach or breadth of supply and show a column a reader recognises. "
    "If the user explicitly asks for a table, or the answer includes multiple comparable data points — "
    "rankings, item/customer breakdowns, trends across periods, etc. — you MUST present them as a single "
    "well-formed markdown table with a header row and a separator row, instead of a prose list, whenever "
    "the data can reasonably be shown that way. Keep every row of that table contiguous — never leave a "
    "blank line between table rows, or between the header and the rows, since a blank line breaks the "
    "table apart. Always express inventory, excess, "
    "and obsolete figures in dollar (USD) value, not unit/quantity counts — if you also have unit "
    "counts, you may include them alongside the dollar value, but never in place of it. Never use or "
    "display a WEEK_KEY, week number, or other week-code column (e.g. '2629') anywhere in your answer, "
    "tables, or charts — when a time dimension is needed, query and show the actual calendar DATE column "
    "instead, and refer to it as a date in your prose (e.g. 'the week of 2026-07-14'), never as a week number."
    + DEFAULT_ALL_SITES_INSTRUCTION +
    " Once more, since this is the rule most often broken: no thinking traces or process narration "
    "of any kind in the final answer — findings and conclusions only.)"
)

# Appended only when the user checks "Concise answer" in the UI.
CONCISE_INSTRUCTION = (
    " (One more thing: the user has asked for a concise, crisp answer — keep it as short as possible "
    "while still stating the key figures and the direct answer. A few sentences, or a short table if "
    "the data calls for one, is enough. Skip elaboration, caveats, background explanation, and extended "
    "narrative unless the question specifically asks for that level of detail.)"
)

# Claude Sonnet pricing per 1M tokens — mirrors static/js/app.js's TOKEN_PRICE
# so usage/cost persisted to history matches what's shown per-answer in the UI.
TOKEN_PRICE = {"uncached": 3.00, "cache_read": 0.30, "cache_write": 3.75, "output": 15.00}


def _usage_tokens_consumed(usage: dict):
    if not usage or not usage.get("tokens_consumed"):
        return None
    return usage["tokens_consumed"][0]


def _calc_total_tokens(usage: dict) -> int:
    tc = _usage_tokens_consumed(usage)
    if not tc:
        return 0
    inp = tc.get("input_tokens") or {}
    out = tc.get("output_tokens") or {}
    return (inp.get("total", 0) or 0) + (out.get("total", 0) or 0)


def _calc_cost(usage: dict) -> float:
    tc = _usage_tokens_consumed(usage)
    if not tc:
        return 0.0
    inp = tc.get("input_tokens") or {}
    out = tc.get("output_tokens") or {}
    return (
        ((inp.get("uncached", 0) or 0) / 1e6) * TOKEN_PRICE["uncached"]
        + ((inp.get("cache_read", 0) or 0) / 1e6) * TOKEN_PRICE["cache_read"]
        + ((inp.get("cache_write", 0) or 0) / 1e6) * TOKEN_PRICE["cache_write"]
        + ((out.get("total", 0) or 0) / 1e6) * TOKEN_PRICE["output"]
    )

RELEVANCE_JUDGE_PROMPT = (
    "You are grading an AI-generated ANSWER against a user QUESTION, like marking "
    "an exam answer out of 100.\n"
    "- If the answer directly addresses what the question actually asked, score "
    "it 100 — no matter how much extra information it also includes. Extra "
    "context beyond the minimum is never a reason to deduct marks.\n"
    "- Only deduct marks when the answer fails to address the question: it's "
    "off-topic, dodges the actual ask, misses a distinct part of a multi-part "
    "question, or states something the question's own subject matter doesn't "
    "support (i.e. looks fabricated rather than genuinely responsive).\n"
    "- The more of the question goes unaddressed, the lower the score — a "
    "completely off-topic answer should score near 0.\n"
    "Respond with ONLY a JSON object of the form "
    '{"relevance_percent": <integer 0-100>} — no other text, no markdown fences.'
)


RELEVANCE_JUDGE_ANSWER_CHAR_CAP = 4000

# Measured against the real endpoint: model inference itself is ~200-600ms
# (per the API's own latency_checkpoint.total_duration_ms) — almost all of
# the 1-2s+ wall-clock cost is TCP/TLS setup to the internal API gateway. A
# module-level Session reuses that connection across calls (each request()
# from a fresh requests.post() pays the handshake again), which is the one
# lever available here since the bulk of the latency isn't inference time.
_azure_openai_session = requests.Session()


def _judge_answer_relevance(question: str, answer: str):
    """LLM-as-judge: scores 0-100 how relevant `answer` is to `question`, via
    the gpt-5.2 Azure OpenAI deployment. Returns None (never 0) on any
    failure — missing config, timeout, bad JSON — so an outage in the judge
    just omits the metric instead of showing a misleading score."""
    if not (AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_VERSION and AZURE_OPENAI_DEPLOYMENT):
        return None
    if not answer:
        return None
    # A huge markdown table/chart narrative doesn't add judging signal beyond
    # its first chunk, but does add prompt-processing time and cost.
    if len(answer) > RELEVANCE_JUDGE_ANSWER_CHAR_CAP:
        answer = answer[:RELEVANCE_JUDGE_ANSWER_CHAR_CAP] + "\n...[truncated]"
    try:
        r = _azure_openai_session.post(
            f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}/chat/completions"
            f"?api-version={AZURE_OPENAI_VERSION}",
            headers={"api-key": AZURE_OPENAI_API_KEY, "Content-Type": "application/json"},
            json={
                "messages": [
                    {"role": "system", "content": RELEVANCE_JUDGE_PROMPT},
                    {"role": "user", "content": f"QUESTION:\n{question}\n\nANSWER:\n{answer}"},
                ],
                "temperature": 0,
                # gpt-5.2 is a reasoning model — its hidden reasoning tokens are
                # deducted from this same budget before the visible JSON reply.
                # In practice this grading task uses 0 reasoning tokens (a
                # short, direct task), so 150 is generous headroom without the
                # earlier 500 cap's larger worst-case wait on a harder call.
                "max_completion_tokens": 150,
            },
            timeout=20,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"].strip()
        content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
        score = json.loads(content)["relevance_percent"]
        return max(0, min(100, int(score)))
    except Exception as e:
        app.logger.warning("Relevance judge call failed: %s", e)
        return None






LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOG_DIR / "interactions.jsonl"
_log_lock = threading.Lock()


def _log_event(event: dict):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with _log_lock:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")


def _load_usage_log(login: str) -> list:
    """Every agent call this user has ever made, in call order — unlike
    history/<user>.json this is never deduped, so it's the source of truth
    for total tokens/cost actually spent. Entries logged before per-user
    tagging existed have no "user" field and are shown to everyone (there's
    no way to know in hindsight whose call it was)."""
    if not LOG_FILE.exists():
        return []
    usage = []
    with LOG_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "agent":
                continue
            if event.get("user") and event.get("user") != login:
                continue
            usage.append({
                "timestamp": event.get("timestamp"),
                "question": event.get("question", ""),
                "total_tokens": event.get("total_tokens", 0),
                "cost": event.get("cost", 0),
            })
    return usage


# ── Per-user question history (persisted across restarts/reloads) ──────────
HISTORY_DIR = Path(__file__).parent / "history"
_history_lock = threading.Lock()


def _history_file_path(login: str) -> Path:
    """All users share one history file — the `login` param is unused here
    but kept so callers don't need to change; conversations are shared,
    unlike the per-user usage log in _load_usage_log."""
    return HISTORY_DIR / "shared_history.json"


def _load_history(login: str) -> list:
    """List of conversations: [{conversation_id, title, started_at, updated_at,
    messages: [{id, question, answer, timestamp}, ...]}], most-recently-active
    conversation last is NOT guaranteed — sort by updated_at when displaying."""
    path = _history_file_path(login)
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    # Defensively drop anything not in the current conversation schema (e.g.
    # entries left over from an older flat question/answer format).
    return [c for c in data if isinstance(c, dict) and isinstance(c.get("messages"), list)]


def _save_history(login: str, conversations: list):
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    with _history_file_path(login).open("w", encoding="utf-8") as f:
        json.dump(conversations, f, indent=2)


# answer they were shown beside: {interaction_id: {answer, cypher, rows, ...}}.
# A side-store rather than a field on the message record because the two calls
# are independent requests — /api/chat appends its message after it finishes
# lands, so writing into the conversation file would be a race. Merged in when
# history is read instead, where ordering no longer matters.










def _append_message_to_conversation(login: str, conversation_id: str, message: dict):
    with _history_lock:
        conversations = _load_history(login)
        conv = next((c for c in conversations if c.get("conversation_id") == conversation_id), None)
        if conv is None:
            conv = {
                "conversation_id": conversation_id,
                "title": message["question"],
                "started_at": message["timestamp"],
                "updated_at": message["timestamp"],
                "messages": [],
            }
            conversations.append(conv)
        conv["messages"].append(message)
        conv["updated_at"] = message["timestamp"]
        _save_history(login, conversations)


def _delete_conversation(login: str, conversation_id: str):
    with _history_lock:
        conversations = _load_history(login)
        conversations = [c for c in conversations if c.get("conversation_id") != conversation_id]
        _save_history(login, conversations)


def _rename_conversation(login: str, conversation_id: str, title: str):
    with _history_lock:
        conversations = _load_history(login)
        for c in conversations:
            if c.get("conversation_id") == conversation_id:
                c["title"] = title
                break
        _save_history(login, conversations)


def _archive_conversation(login: str, conversation_id: str, archived: bool):
    with _history_lock:
        conversations = _load_history(login)
        for c in conversations:
            if c.get("conversation_id") == conversation_id:
                c["archived"] = archived
                break
        _save_history(login, conversations)


def _get_remote_login() -> str:
    """The Windows login of whoever is hitting this request through their
    browser. In production this requires IIS Windows Authentication enabled
    on the site, with a URL Rewrite rule forwarding the LOGON_USER server
    variable as the X-Remote-User request header — httpPlatformHandler
    proxies requests to this app over plain HTTP, so IIS's authenticated
    identity isn't otherwise visible here. Browsers have no API to expose
    the OS username directly, so this header (or REMOTE_USER/LOGON_USER, if
    a future hosting setup provides them in the WSGI environ) is the only
    legitimate source. Locally, with no IIS in front, falls back to the
    account running `python app.py`."""
    remote_user = (
        request.headers.get("X-Remote-User")
        or request.environ.get("REMOTE_USER")
        or request.environ.get("LOGON_USER")
    )
    if remote_user:
        return remote_user.split("\\")[-1]  # strip a "DOMAIN\" prefix if present
    return getpass.getuser()


DEFAULT_USER_DISPLAY_NAME = "Demo User"
DEFAULT_USER_INITIALS = "DU"


def _resolve_identity() -> dict:
    """`login` is still resolved per-request (see _get_remote_login) so each
    browser user's Recents/history stays separate on disk. The display name
    shown in the UI is intentionally a fixed generic label — resolving each
    visitor's real name reliably needs IIS Windows Authentication properly
    forwarding it (see _get_remote_login's docstring), which isn't wired up
    here, so rather than show a wrong or inconsistent name we show none."""
    return {"login": _get_remote_login(), "full_name": DEFAULT_USER_DISPLAY_NAME, "initials": DEFAULT_USER_INITIALS}


def _split_thinking(text):
    """Split a thinking blob into individual paragraph steps."""
    parts = re.split(r'\n{2,}', text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 20]

app = Flask(__name__)


def _friendly_error_message(exc: Exception) -> str:
    """Map a low-level exception to a message that's safe to show end users —
    the real exception (status codes, hostnames, stack trace) is always
    logged server-side for debugging, but never sent to the browser."""
    app.logger.error("Request to the graph/LLM service failed", exc_info=exc)

    if isinstance(exc, requests.exceptions.Timeout):
        return "The graph service took too long to respond. Please try again in a moment."
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "We couldn't reach the data service right now. Please check your connection and try again shortly."
    if isinstance(exc, requests.exceptions.HTTPError):
        status = exc.response.status_code if exc.response is not None else None
        if status in (401, 403):
            return "Authentication with the data service failed. Please contact your administrator to refresh access."
        if status and status >= 500:
            return "The graph service is temporarily unavailable. Please try again in a few minutes."
        return "Something went wrong while fetching your answer. Please try again."
    return "Something went wrong while processing your question. Please try again."














# app used before, it takes a real English question and returns an actual
# analysis (answer text, the algorithm/records it used, token usage) — no
# computation per call, so it can take 30+ seconds.






# can reveal the answer as it is composed instead of waiting out the whole call.
#
# Its wire format is bare SSE data frames carrying a "type" discriminator:
#   session | stage | plan | cypher | step_done | rows | token | done | error
# The proxy below translates that into the named-event convention the rest of
# this app's endpoints use (event: text_delta / plan / stage / done / error) and
# reshapes the row dicts into the columns + row-arrays shape renderResultTable
# section on the page.
# this process rather than called over HTTP. Its modules import each other by
# plain top-level name (`import config`, `import graph`), so the package
# directory goes on sys.path and they are imported as they expect. None of those
# names collide with anything here or in site-packages.
#
# and a missing AWS credential should fail that one question rather than stop
# the whole app from starting.



# Appended to the question on its way upstream. Left to itself the service
# which reads as data-science homework to the people using this — they want to
# know which parts and customers are exposed, not which algorithm found them.
# The service still picks whatever approach it likes; this only constrains how
# anyone who does want the mechanics.

# Supplier questions are sent exactly as typed, with no style guidance attached.
# Vendor counts as the same subject — it is the word half the business uses for
# it — so both stems are matched.




def _sse(event: str, data: dict) -> str:
    return "event: " + event + "\ndata: " + json.dumps(data) + "\n\n"


# Money figures asserted by the question itself: "$493M", "$1.2 billion",
# "$493,006,890". A bare number is ignored — "site 059" and "top 10" are not
# claims about a total.
# How far off a result can be and still count as reproducing the figure. Wide
# enough for rounding in the question ("$493M" for 493,006,890) without letting
# a different measure through.






def _fmt_usd_compact(value: float) -> str:
    absolute = abs(value)
    if absolute >= 1e9:
        return f"${value / 1e9:.2f}B"
    if absolute >= 1e6:
        return f"${value / 1e6:.1f}M"
    if absolute >= 1e3:
        return f"${value / 1e3:.1f}K"
    return f"${value:.0f}"




def _rows_to_table(rows):
    """[{a: 1, b: 2}, ...] -> (["a", "b"], [[1, 2], ...]).

    Columns are the union of every row's keys in first-seen order, so a row
    that omits a key (or a later row that introduces one) still lines up.
    Non-scalar values (a returned node or path object) are JSON-encoded so the
    cell renders as text instead of "[object Object]"."""
    if not rows or not isinstance(rows, list):
        return None, None
    columns = []
    for row in rows:
        if not isinstance(row, dict):
            return None, None
        for key in row:
            if key not in columns:
                columns.append(key)
    table = []
    for row in rows:
        cells = []
        for col in columns:
            val = row.get(col)
            if isinstance(val, (dict, list)):
                val = json.dumps(val)
            cells.append(val)
        table.append(cells)
    return columns, table




@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    body = request.get_json(silent=True) or {}
    rating = body.get("rating")
    if rating not in ("up", "down"):
        return jsonify({"error": "rating must be 'up' or 'down'."}), 400
    question = body.get("question", "")
    _log_event({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "interaction_id": body.get("interaction_id"),
        "type": "feedback",
        "user": _get_remote_login(),
        "rating": rating,
        "question": question,
        "answer": body.get("answer", ""),
    })
    return jsonify({"ok": True})


@app.route("/")
def index():
    identity = _resolve_identity()
    return render_template(
        "index.html",
        sample_questions=random.sample(SAMPLE_QUESTIONS, k=min(SAMPLE_QUESTIONS_SHOWN, len(SAMPLE_QUESTIONS))),
        user_full_name=identity["full_name"],
        user_initials=identity["initials"],
        initial_history=_load_history(identity["login"]),
    )


@app.route("/api/dashboard-metrics")
def api_dashboard_metrics():
    with _dashboard_metrics_lock:
        data = _dashboard_metrics_cache["data"]
        fetched_at = _dashboard_metrics_cache["fetched_at"]
        error = _dashboard_metrics_cache["error"]
    if data is None:
        return jsonify({"loading": True, "error": error})
    payload = dict(data)
    payload["fetched_at"] = fetched_at
    return jsonify(payload)


# Serializes manual refresh clicks so two people (or a double-click) hitting
# this at once share one agent call instead of firing duplicates.
_dashboard_metrics_refresh_lock = threading.Lock()


@app.route("/api/dashboard-metrics/refresh", methods=["POST"])
def api_dashboard_metrics_refresh():
    with _dashboard_metrics_refresh_lock:
        _refresh_dashboard_metrics_cache()
    with _dashboard_metrics_lock:
        data = _dashboard_metrics_cache["data"]
        fetched_at = _dashboard_metrics_cache["fetched_at"]
        error = _dashboard_metrics_cache["error"]
    if data is None:
        return jsonify({"error": error or "Refresh failed."}), 502
    payload = dict(data)
    payload["fetched_at"] = fetched_at
    return jsonify(payload)






@app.route("/api/history")
def api_history_get():
    return jsonify({"history": _load_history(_resolve_identity()["login"])})


@app.route("/api/history/delete", methods=["POST"])
def api_history_delete():
    body = request.get_json(silent=True) or {}
    conversation_id = body.get("conversation_id")
    if not conversation_id:
        return jsonify({"error": "conversation_id is required."}), 400
    _delete_conversation(_resolve_identity()["login"], conversation_id)
    return jsonify({"ok": True})


@app.route("/api/history/rename", methods=["POST"])
def api_history_rename():
    body = request.get_json(silent=True) or {}
    conversation_id = body.get("conversation_id")
    title = (body.get("title") or "").strip()
    if not conversation_id or not title:
        return jsonify({"error": "conversation_id and title are required."}), 400
    _rename_conversation(_resolve_identity()["login"], conversation_id, title)
    return jsonify({"ok": True})


@app.route("/api/history/archive", methods=["POST"])
def api_history_archive():
    body = request.get_json(silent=True) or {}
    conversation_id = body.get("conversation_id")
    archived = bool(body.get("archived"))
    if not conversation_id:
        return jsonify({"error": "conversation_id is required."}), 400
    _archive_conversation(_resolve_identity()["login"], conversation_id, archived)
    return jsonify({"ok": True})


@app.route("/api/usage")
def api_usage_get():
    return jsonify({"usage": _load_usage_log(_get_remote_login())})


def _build_chat_payload(interaction_id, conversation_id, answer_text, sql, suggestions, elapsed,
                         columns, rows, table_title, chart_payload, usage, reasoning_steps,
                         relevance_percent=None):
    payload = {
        "answer": answer_text, "sql": sql, "suggestions": suggestions, "elapsed": elapsed,
        "interaction_id": interaction_id, "conversation_id": conversation_id,
    }
    if columns is not None:
        payload["columns"] = columns
        payload["rows"] = rows
    if table_title:
        payload["tableTitle"] = table_title
    if chart_payload:
        if "vegaSpec" in chart_payload:
            payload["vegaSpec"] = chart_payload["vegaSpec"]
        if chart_payload.get("chartjs"):
            payload["chart"] = chart_payload["chartjs"]
    if usage:
        payload["usage"] = usage
    if reasoning_steps:
        payload["reasoningSteps"] = reasoning_steps
    if relevance_percent is not None:
        payload["relevance_percent"] = relevance_percent
    return payload


def _build_chat_message_record(interaction_id, question, answer_text, now_iso, sql, elapsed,
                                columns, rows, table_title, chart_payload, usage, reasoning_steps,
                                relevance_percent=None):
    record = {
        "id": interaction_id, "question": question, "answer": answer_text, "timestamp": now_iso,
        "has_sql": bool(sql), "sql": sql, "elapsed": elapsed,
    }
    if columns is not None:
        record["columns"] = columns
        record["rows"] = rows
    if table_title:
        record["table_title"] = table_title
    if chart_payload:
        if "vegaSpec" in chart_payload:
            record["vega_spec"] = chart_payload["vegaSpec"]
        if chart_payload.get("chartjs"):
            record["chart"] = chart_payload["chartjs"]
    if usage:
        record["usage"] = usage
    if reasoning_steps:
        record["reasoning_steps"] = reasoning_steps
    if relevance_percent is not None:
        record["relevance_percent"] = relevance_percent
    return record


# Answers are never cached: every question runs the agent live, so what comes
# back always reflects the data as it is now rather than as it was when the
# same wording was last asked.


# ═══════════════════════════════════════════════════════════════════════════
# The engine: question -> Snowflake Cortex Data Agent -> narrated answer
# ═══════════════════════════════════════════════════════════════════════════
_llm = requests.Session()


def _azure_chat(system: str, user: str, max_tokens: int = 1200, temperature: float = 0):
    """One Azure OpenAI chat completion. Returns (text, usage_dict)."""
    r = _llm.post(
        f"{AZURE_OPENAI_ENDPOINT}/openai/deployments/{AZURE_OPENAI_DEPLOYMENT}"
        f"/chat/completions?api-version={AZURE_OPENAI_VERSION}",
        headers={"api-key": AZURE_OPENAI_API_KEY, "Content-Type": "application/json"},
        json={"messages": [{"role": "system", "content": system},
                           {"role": "user", "content": user}],
              "temperature": temperature,
              "max_completion_tokens": max_tokens},
        timeout=90,
    )
    r.raise_for_status()
    body = r.json()
    return body["choices"][0]["message"]["content"], (body.get("usage") or {})


# How much of the conversation travels with each question. agent:run keeps no
# server-side state, so this replay IS the chat's memory — get it wrong and
# follow-ups like "and the third one?" have nothing to resolve against.
#
# The budget matters more than it looks. Answers here are mostly markdown
# tables, and a tight per-answer cap truncates them mid-table: the follow-up
# then sees a header and two rows of something the user can still see fifteen
# rows of on screen. The caps below keep whole small tables intact while
# bounding what a long conversation can add to a prompt.
HISTORY_TURNS        = 6     # turns replayed, newest first
HISTORY_ANSWER_CHARS = 1500  # per answer
HISTORY_TOTAL_CHARS  = 8000  # across the whole replayed transcript


def _history_context(history: list) -> str:
    """Recent turns as a transcript, so follow-ups resolve.

    The agent:run endpoint holds no server-side conversation state, so this is
    the only thing carrying context between turns — it is sent on every
    request (see _agent_request).

    Built newest-first and reversed at the end: when the total budget runs out
    it is the oldest turns that get dropped, never the most recent one, which
    is the turn a follow-up almost always refers to.
    """
    turns, budget = [], HISTORY_TOTAL_CHARS
    for h in reversed(history or []):
        if len(turns) >= HISTORY_TURNS or budget <= 0:
            break
        question = (h.get("question") or "").strip()
        answer = (h.get("answer") or "").strip()
        if not (question or answer):
            continue
        if len(answer) > HISTORY_ANSWER_CHARS:
            answer = answer[:HISTORY_ANSWER_CHARS].rstrip() + "\n[...truncated]"
        block = f"User: {question}\nAssistant: {answer}" if answer else f"User: {question}"
        budget -= len(block)
        turns.append(block)
    if not turns:
        return ""
    transcript = "\n\n".join(reversed(turns))
    return (
        "Here is the conversation so far, for context only — do not answer these "
        "again. Use them to resolve references in the new question (\"those\", "
        "\"the third one\", \"same but for last year\"), and prefer re-querying the "
        "data over trusting any figure quoted below.\n"
        "<conversation_so_far>\n" + transcript + "\n</conversation_so_far>"
    )


# ── Snowflake connections ───────────────────────────────────────────────────
# Flask serves each request on its own thread and a Snowflake connection is
# not thread-safe, so every thread gets (and reuses) its own. Reusing matters:
# opening one is a full TLS handshake plus a login round-trip, which is a
# large fraction of a fast query's wall-clock cost.
_sf_local = threading.local()


def _sf_connect():
    return snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        authenticator="programmatic_access_token",
        token=SNOWFLAKE_TOKEN,
        role=SNOWFLAKE_ROLE,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA,
        client_session_keep_alive=True,
        network_timeout=AGENT_TIMEOUT,
    )


def _sf_conn():
    conn = getattr(_sf_local, "conn", None)
    if conn is None or conn.is_closed():
        conn = _sf_connect()
        _sf_local.conn = conn
    return conn


def _sf_drop_conn():
    """Throw this thread's connection away so the next call reconnects."""
    conn = getattr(_sf_local, "conn", None)
    _sf_local.conn = None
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass


def _jsonable(v):
    """Snowflake values -> JSON-safe primitives the frontend can render."""
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, Decimal):
        # int when it is one, so counts don't render as "12.0"
        return int(v) if v == v.to_integral_value() else float(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf-8", "replace")
    return str(v)


# A dead session and a rejected statement need opposite handling: the first is
# worth retrying verbatim on a fresh connection, the second never is.
SF_FAULT_MARKERS = (
    "authentication token has expired", "session no longer exists",
    "connection is closed", "connection was closed", "forcibly closed",
    "connection reset", "connection aborted", "session expired",
)


def is_db_fault(exc: Exception) -> bool:
    """True when the failure is the connection/session, not the statement."""
    if isinstance(exc, (snowflake.connector.errors.OperationalError,
                        snowflake.connector.errors.InterfaceError,
                        requests.exceptions.ConnectionError)):
        return True
    text = str(exc).lower()
    return any(m in text for m in SF_FAULT_MARKERS)


def sf_query(sql: str, params=None, max_rows: int = None, timeout: int = None):
    """Execute one read-only statement. Returns (columns, rows).

    A dropped session is retried once on a fresh connection — PATs and idle
    sessions both expire on their own schedule, and the first query after
    either is otherwise guaranteed to fail for reasons the statement itself
    has nothing to do with.
    """
    cap = MAX_ROWS if max_rows is None else max_rows
    for attempt in (0, 1):
        cur = None
        try:
            cur = _sf_conn().cursor()
            cur.execute(sql, params, timeout=timeout or SQL_TIMEOUT)
            columns = [c[0] for c in (cur.description or [])]
            rows = [[_jsonable(v) for v in r] for r in cur.fetchmany(cap)]
            return columns, rows
        except Exception as exc:
            if attempt == 0 and is_db_fault(exc):
                app.logger.warning("Snowflake session fault, reconnecting: %s", exc)
                _sf_drop_conn()
                continue
            raise
        finally:
            if cur is not None:
                try:
                    cur.close()
                except Exception:
                    pass


# ── Cortex Agents REST API ──────────────────────────────────────────────────
# POST /api/v2/cortex/agent:run, with the tool definitions sent inline on every
# request rather than read from a stored AGENT object.
#
# Sending them inline is the point: the agent's tools, model and instructions
# live in this file, under version control, and changing them is a code edit
# rather than a Snowflake DDL statement against a shared object that other
# clients may also be calling. It also means the app has no deployment step
# beyond itself — there is no stored agent to create, grant or keep in sync.
#
# The reply is one JSON document with a `content` array of typed blocks
# (text / thinking / tool_use / tool_result / table / chart /
# suggested_queries), a `status`, and a `metadata` block carrying token usage.
AGENT_URL = f"https://{SNOWFLAKE_HOST}/api/v2/cortex/agent:run"

# The orchestration model. Pinned rather than "auto" so answer style and cost
# stay predictable between deployments.
AGENT_MODEL = os.environ.get("CORTEX_AGENT_MODEL", "claude-sonnet-4-6")

AGENT_TOOLS = [
    {"tool_spec": {
        "type": "cortex_analyst_text_to_sql",
        "name": "kg_analyst",
        "description": (
            "Supply-chain knowledge graph: nodes (suppliers, supplier sites, parts, "
            "products, plants, warehouses, customers, lanes, ports, carriers, "
            "countries, commodities) and the edges between them, with precomputed "
            "PageRank, degree, HITS hub/authority, betweenness and connected "
            "components."),
    }},
    {"tool_spec": {
        "type": "cortex_search",
        "name": "kg_search",
        "description": (
            "Unstructured supply-chain documents: supplier contracts, "
            "non-conformance reports, supplier scorecards and risk alerts."),
    }},
    {"tool_spec": {"type": "sql_exec", "name": "sql_exec",
                   "description": "Executes the generated SQL on the warehouse."}},
    {"tool_spec": {"type": "data_to_chart", "name": "data_to_chart",
                   "description": "Generates visualizations from returned data."}},
]

AGENT_TOOL_RESOURCES = {
    "kg_analyst": {
        "semantic_view": SEMANTIC_VIEW,
        "execution_environment": {"type": "warehouse",
                                  "warehouse": SNOWFLAKE_WAREHOUSE},
    },
    "kg_search": {"search_service": SEARCH_SERVICE, "max_results": "5"},
}

AGENT_ORCHESTRATION_INSTRUCTION = (
    "Use the kg_analyst tool for anything about entities and their relationships — "
    "suppliers, supplier sites, parts, products, plants, warehouses, customers, "
    "lanes, ports, carriers and countries — including graph analytics such as "
    "importance (PAGERANK), connectivity (DEGREE_TOTAL), bottlenecks (BETWEENNESS) "
    "and communities (COMPONENT_ID). Use the kg_search tool for questions about "
    "contracts, non-conformance reports, supplier scorecards and risk alerts. "
    "Always execute the SQL you generate with sql_exec and answer from the rows it "
    "returns — never present un-executed SQL as the answer."
)

# A PAT is not a Snowflake OAuth token, and the endpoint assumes OAuth unless
# told otherwise — without this header a valid PAT comes back 401.
_agent_session = requests.Session()
_agent_session.headers.update({
    "Authorization": f"Bearer {SNOWFLAKE_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-Snowflake-Authorization-Token-Type": "PROGRAMMATIC_ACCESS_TOKEN",
})


def _agent_request(question: str, history: list, concise: bool) -> dict:
    """Build the request body for one turn.

    The style rules travel with the question rather than sitting only in the
    agent's own instructions, so a caller-side toggle like "concise" can change
    them per request.
    """
    prompt = question + ANSWER_STYLE_INSTRUCTION + (CONCISE_INSTRUCTION if concise else "")
    # This endpoint holds no server-side conversation state, so prior turns are
    # replayed as context — otherwise "and for last quarter?" has nothing to
    # resolve against.
    ctx = _history_context(history)
    if ctx:
        prompt = f"{ctx}\n\nQuestion: {prompt}"
    return {
        "models": {"orchestration": AGENT_MODEL},
        "instructions": {
            "response": ANSWER_RESPONSE_INSTRUCTION,
            "orchestration": AGENT_ORCHESTRATION_INSTRUCTION,
        },
        "tools": AGENT_TOOLS,
        "tool_resources": AGENT_TOOL_RESOURCES,
        "messages": [{"role": "user",
                      "content": [{"type": "text", "text": prompt}]}],
        "stream": False,
    }


def cortex_agent_run(question: str, history: list, concise: bool) -> dict:
    """One synchronous agent turn. Returns the raw response document."""
    resp = _agent_session.post(AGENT_URL, json=_agent_request(question, history, concise),
                               timeout=AGENT_TIMEOUT)
    if resp.status_code != 200:
        # The body carries Snowflake's actual complaint (bad semantic view,
        # expired token, missing privilege); the status alone never says which.
        app.logger.error("Cortex agent HTTP %s: %s", resp.status_code, resp.text[:2000])
        resp.raise_for_status()
    try:
        return resp.json()
    except ValueError as e:
        app.logger.error("Cortex agent returned non-JSON: %s", resp.text[:2000])
        raise RuntimeError(f"Cortex agent returned a non-JSON response: {e}") from e


def _agent_block_text(block: dict) -> str:
    """Text out of a content block whose payload may be either a bare string
    or a {"text": ...} object — both shapes occur across block types."""
    for key in ("text", "thinking", "content"):
        val = block.get(key)
        if isinstance(val, str):
            return val
        if isinstance(val, dict) and isinstance(val.get("text"), str):
            return val["text"]
    return ""


def _find_in_json(node, wanted: str, depth: int = 0):
    """First value for `wanted` anywhere in a nested structure.

    The agent's tool_results are shaped by whichever tool ran (Cortex Analyst,
    SQL execution, search), and each nests its payload differently. Rather
    than hard-code one tool's layout, this looks for the key wherever it sits.
    """
    if depth > 8:
        return None
    if isinstance(node, dict):
        if wanted in node:
            return node[wanted]
        for v in node.values():
            found = _find_in_json(v, wanted, depth + 1)
            if found is not None:
                return found
    elif isinstance(node, list):
        for v in node:
            found = _find_in_json(v, wanted, depth + 1)
            if found is not None:
                return found
    return None


# Snowflake reports a column's type in its result metadata, but the values
# themselves arrive as strings — including numbers. Left as strings a ranking
# renders right-aligned-looking but sorts and charts as text, so numeric
# columns are converted back using the declared type rather than by guessing
# at the value.
_SF_NUMERIC_TYPES = {"fixed", "real", "number", "float", "double", "integer", "decimal"}


def _coerce_sf_value(value, sf_type: str):
    if value is None or sf_type not in _SF_NUMERIC_TYPES:
        return _jsonable(value)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _jsonable(value)
    return int(number) if number.is_integer() else number


def _result_set_to_table(result_set):
    """Snowflake's REST result_set shape -> (columns, rows)."""
    if not isinstance(result_set, dict):
        return None, None
    meta = result_set.get("resultSetMetaData") or {}
    row_type = meta.get("rowType") or []
    columns = [c.get("name") for c in row_type if isinstance(c, dict)]
    types = [str(c.get("type", "")).lower() for c in row_type if isinstance(c, dict)]
    data = result_set.get("data")
    if not (columns and isinstance(data, list)):
        return None, None
    rows = []
    for row in data[:MAX_ROWS]:
        if not isinstance(row, (list, tuple)):
            continue
        rows.append([_coerce_sf_value(v, types[i] if i < len(types) else "")
                     for i, v in enumerate(row)])
    return (columns, rows) if rows else (None, None)


# Block types that represent the agent working rather than answering. Text
# emitted before the last of these is inter-step narration ("I'll query the
# graph next"), not part of the final answer — see _parse_agent_response.
_AGENT_WORK_BLOCKS = ("tool_use", "tool_result", "tool_results", "table")


def _parse_agent_response(resp: dict) -> dict:
    """Flatten one agent response document into the pieces the UI needs.

    Content blocks are typed and the mix varies per question — a plain answer
    is text only, a data question adds thinking, tool_use and tool_result, and
    a chartable one adds a chart spec. Everything below is best-effort: an
    unrecognised or missing block leaves its field None rather than failing
    the turn, since the answer text is the only part that must be there.
    """
    content = [b for b in (resp.get("content") or []) if isinstance(b, dict)]

    # The agent narrates between tool calls ("I'll fix the query and retry"),
    # and those are plain text blocks too. Only the text after its last tool
    # step is the answer it actually stands behind; taking everything would
    # paste its working notes on top of the finished write-up.
    last_work = -1
    for i, block in enumerate(content):
        if block.get("type") in _AGENT_WORK_BLOCKS:
            last_work = i

    answer_parts, thinking_parts, suggestions = [], [], []
    sql = executed_sql = None
    columns = rows = None
    vega_spec = None

    for i, block in enumerate(content):
        btype = block.get("type")
        if btype == "text":
            text = _agent_block_text(block)
            if i > last_work:
                answer_parts.append(text)
            elif text.strip():
                # Narration still makes a decent progress trace for the
                # thinking card, which is where process commentary belongs.
                thinking_parts.append(text.strip())
        elif btype == "thinking":
            text = _agent_block_text(block).strip()
            if text:
                thinking_parts.append(text)
        elif btype == "chart":
            spec = _find_in_json(block, "chart_spec")
            if isinstance(spec, str):
                try:
                    spec = json.loads(spec)
                except ValueError:
                    spec = None
            if isinstance(spec, dict):
                vega_spec = spec
        elif btype == "suggested_queries":
            for item in (block.get("suggested_queries") or []):
                if isinstance(item, dict) and item.get("query"):
                    suggestions.append(str(item["query"]))
                elif isinstance(item, str):
                    suggestions.append(item)
        elif btype in _AGENT_WORK_BLOCKS:
            found_sql = _find_in_json(block, "sql")
            if isinstance(found_sql, str) and found_sql.strip():
                # Several blocks carry a "sql" key: the Analyst tool proposes
                # one, and the execution tool reports the one it actually ran
                # (logical names expanded to real tables). Keep any of them as
                # a fallback, but the pair below is what gets preferred.
                sql = sql or found_sql.strip()

            cols, tbl = _result_set_to_table(_find_in_json(block, "result_set"))
            if cols is None:
                # A "table" block carries plain columns/rows instead.
                raw_cols = _find_in_json(block, "columns")
                raw_rows = _find_in_json(block, "rows")
                if isinstance(raw_cols, list) and isinstance(raw_rows, list):
                    cols = [str(c) for c in raw_cols]
                    tbl = [[_jsonable(v) for v in r] for r in raw_rows[:MAX_ROWS]
                           if isinstance(r, (list, tuple))]
            if cols and tbl:
                # LAST wins, not first. An agent commonly runs an exploratory
                # query, then a corrected or refined one, and writes its answer
                # from the final result — so keeping the first would show a
                # table that contradicts the prose above it. Taking the SQL
                # from this same block also keeps the two consistent.
                columns, rows = cols, tbl
                if isinstance(found_sql, str) and found_sql.strip():
                    executed_sql = found_sql.strip()

    answer = "\n".join(p for p in answer_parts if p).strip()
    if not answer:
        # The agent sometimes finishes with a tool step rather than prose — a
        # final charting call, say — leaving no text after the last work block.
        # Its earlier text is then the whole answer, and showing that with a
        # little narration in it beats showing nothing at all.
        answer = "\n".join(thinking_parts).strip()

    metadata = resp.get("metadata") or {}
    return {
        "answer": answer,
        "thinking": thinking_parts,
        "sql": executed_sql or sql,
        "columns": columns,
        "rows": rows,
        "vega_spec": vega_spec,
        "suggestions": suggestions,
        "usage": metadata.get("usage") or {},
        "status": resp.get("status"),
    }


# ── Follow-up suggestions (optional, Azure OpenAI) ──────────────────────────
SUGGESTION_SYSTEM_PROMPT = (
    "You suggest what a supply-chain analyst would naturally ask next, given the "
    "question they just asked and the answer they got. Each suggestion must be a "
    "complete, standalone question that makes sense on its own without the previous "
    "turn for context, and must be answerable from supply-chain inventory data "
    "(parts, suppliers, sites, plants, customers, shipments, inventory value and "
    "days-of-inventory). Respond with ONLY a JSON array of 3-5 question strings — "
    "no other text, no markdown fences."
)


def extract_json(text: str):
    """First JSON value in a model reply, tolerating ```json fences."""
    if not text:
        return None
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except ValueError:
        pass
    match = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except ValueError:
        return None


def followup_suggestions(question: str, answer: str):
    if not (AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT
            and AZURE_OPENAI_VERSION and AZURE_OPENAI_DEPLOYMENT):
        return []
    try:
        text, _ = _azure_chat(SUGGESTION_SYSTEM_PROMPT,
                              f"Question: {question}\n\nAnswer: {answer[:1500]}",
                              max_tokens=300)
        got = extract_json(text)
        if isinstance(got, list):
            return [str(q) for q in got
                    if not any(t in str(q).lower() for t in SUPPRESSED_SUGGESTION_TERMS)][:5]
    except Exception as e:
        app.logger.warning("suggestion call failed: %s", e)
    return []


def _chart_from_rows(columns, rows):
    """A chart when the rows have a label column plus a numeric column.

    A ranking usually also carries snapshot_date as its first column; using
    that as the x-axis would draw a flat line, so a non-date label column is
    preferred and the date is only used when it is the only label available
    (which is exactly the trend-over-time case that should be a line).
    """
    if not columns or not rows or len(columns) < 2 or len(rows) < 2:
        return None

    def is_date_col(i):
        return all(isinstance(r[i], str) and re.match(r"^\d{4}-\d{2}-\d{2}", r[i])
                   for r in rows)

    str_cols = [i for i in range(len(columns))
                if all(isinstance(r[i], str) for r in rows)]
    if not str_cols:
        return None
    non_date = [i for i in str_cols if not is_date_col(i)]
    # among non-date labels prefer the one that actually varies across rows
    if non_date:
        label_i = max(non_date, key=lambda i: len({r[i] for r in rows}))
    else:
        label_i = str_cols[0]

    value_i = next((i for i in range(len(columns))
                    if i != label_i and all(isinstance(r[i], (int, float))
                                            and not isinstance(r[i], bool)
                                            for r in rows)), None)
    if value_i is None:
        return None
    if len({r[label_i] for r in rows}) < 2:
        return None

    labels = [str(r[label_i]) for r in rows][:25]
    values = [r[value_i] for r in rows][:25]
    return {
        "type": "line" if is_date_col(label_i) else "bar",
        "labels": labels,
        "datasets": [{"label": columns[value_i].replace("_", " ").title(), "data": values}],
        "yFormat": "$" if "usd" in columns[value_i].lower() else None,
    }


# Landing-page summary, straight from Snowflake. Every tile is a column or a
# status value the schema already carries — nothing here is a derived E&O
# classification this data doesn't actually make:
#
#   inventory value   SUM(ON_HAND_VALUE) at the newest snapshot
#   median DOI        MEDIAN(DOI) — median, not mean, because a handful of
#                     never-consumed parts push the mean to ~4x the typical part
#   open PO value     PO lines whose header is still OPEN or PARTIAL
#   delayed shipments SHIPMENT_HEADER.STATUS = 'DELAYED'
#   EOL parts         DIM_PART.LIFECYCLE_STATUS in ('OBSOLETE', 'EOL')
#   customers         rows in DIM_CUSTOMER
#
# MAX(SNAPSHOT_DATE) still scopes the inventory figures to the newest
# snapshot; it is simply no longer reported as a tile of its own.
DASHBOARD_SQL = """
WITH latest AS (
    SELECT MAX(SNAPSHOT_DATE) AS D FROM SCS.INVENTORY.FACT_INVENTORY_SNAPSHOT
), snap AS (
    SELECT
        ROUND(SUM(f.ON_HAND_VALUE), 2)       AS INVENTORY_VALUE_USD,
        ROUND(MEDIAN(f.DOI), 1)              AS MEDIAN_DOI,
        COUNT(DISTINCT f.PART_ID)            AS PARTS_STOCKED
    FROM SCS.INVENTORY.FACT_INVENTORY_SNAPSHOT f
    JOIN latest ON f.SNAPSHOT_DATE = latest.D
)
SELECT
    snap.INVENTORY_VALUE_USD,
    snap.MEDIAN_DOI,
    snap.PARTS_STOCKED,
    (SELECT ROUND(SUM(l.QUANTITY * l.UNIT_PRICE), 2)
       FROM SCS.INVENTORY.PO_HEADER h
       JOIN SCS.INVENTORY.PO_LINE l ON l.PO_ID = h.PO_ID
      WHERE h.STATUS IN ('OPEN', 'PARTIAL'))                  AS OPEN_PO_VALUE_USD,
    (SELECT COUNT(*) FROM SCS.INVENTORY.SHIPMENT_HEADER
      WHERE STATUS = 'DELAYED')                               AS DELAYED_SHIPMENTS,
    (SELECT COUNT(*) FROM SCS.INVENTORY.DIM_PART
      WHERE LIFECYCLE_STATUS IN ('OBSOLETE', 'EOL'))          AS EOL_PARTS,
    (SELECT COUNT(*) FROM SCS.INVENTORY.DIM_CUSTOMER)         AS NUM_CUSTOMERS
FROM snap
"""


def _fetch_dashboard_metrics():
    """Landing-page tiles, straight from Snowflake. The returned keys are the
    exact ones renderDashboardMetrics() in static/js/app.js reads, since
    /api/dashboard-metrics passes this dict through unchanged."""
    columns, rows = sf_query(DASHBOARD_SQL, max_rows=1)
    if not rows:
        raise RuntimeError("dashboard query returned no rows")
    d = dict(zip(columns, rows[0]))
    return {
        "inventory_value_usd":  d.get("INVENTORY_VALUE_USD") or 0,
        "median_doi":           d.get("MEDIAN_DOI") or 0,
        "open_po_value_usd":    d.get("OPEN_PO_VALUE_USD") or 0,
        "delayed_shipments":    d.get("DELAYED_SHIPMENTS") or 0,
        "eol_parts":            d.get("EOL_PARTS") or 0,
        "num_customers":        d.get("NUM_CUSTOMERS") or 0,
    }


def _refresh_dashboard_metrics_cache():
    """Recompute the landing-page tiles. Writes BOTH the in-memory cache that
    /api/dashboard-metrics{,/refresh} serve from and the on-disk copy that
    survives a restart."""
    try:
        data = _fetch_dashboard_metrics()
        fetched_at = datetime.now(timezone.utc).isoformat()
        with _dashboard_metrics_lock:
            _dashboard_metrics_cache["data"] = data
            _dashboard_metrics_cache["fetched_at"] = fetched_at
            _dashboard_metrics_cache["error"] = None
        _save_dashboard_metrics(data, fetched_at)
        return {"metrics": data, "fetched_at": fetched_at}
    except Exception as e:
        app.logger.warning("dashboard metric refresh failed: %s", e)
        with _dashboard_metrics_lock:
            _dashboard_metrics_cache["error"] = "Unavailable"
        return None


@app.route("/api/chat", methods=["POST"])
def api_chat():
    from flask import Response, stream_with_context
    body = request.get_json(silent=True) or {}
    question = (body.get("question") or "").strip()
    history = body.get("history") or []
    concise = bool(body.get("concise"))
    conversation_id = body.get("conversation_id") or str(uuid.uuid4())
    login = _get_remote_login()
    if not question:
        return jsonify({"error": "Question is required."}), 400

    def generate():
        t0 = time.time()
        try:
            yield _sse("thinking_delta",
                       {"text": "Sending the question to the Snowflake Cortex agent.\n\n"})

            resp = cortex_agent_run(question, history, concise)
            parsed = _parse_agent_response(resp)

            # The agent reports its own terminal state; anything other than a
            # completed run means the answer text (if any) is partial, and
            # saying so beats presenting a truncated answer as final.
            if parsed["status"] not in (None, "completed") and not parsed["answer"]:
                app.logger.warning("agent run ended as %s: %s",
                                   parsed["status"], json.dumps(resp)[:2000])
                yield _sse("error", {"error":
                    "The Cortex agent didn't finish this run. Please try again, "
                    "or rephrase the question a little."})
                return

            # The agent's own reasoning becomes the planning card's trace.
            for step in parsed["thinking"]:
                yield _sse("thinking_delta", {"text": step.strip() + "\n\n"})

            answer_text = (parsed["answer"] or "").strip()
            if not answer_text:
                yield _sse("error", {"error":
                    "The Cortex agent returned an empty answer. Try rephrasing the "
                    "question — for example \"most critical suppliers\" or "
                    "\"which parts are single-sourced\"."})
                return

            yield _sse("text_delta", {"text": answer_text})

            # Structured results when the agent's tools returned any; the
            # markdown table it wrote into the answer text otherwise.
            columns, rows = parsed["columns"], parsed["rows"]
            if columns is None:
                columns, rows = _extract_markdown_table(answer_text)
            if columns:
                columns, rows = _strip_week_columns(columns, rows)
                columns, rows = _strip_suppressed_columns(columns, rows)

            chart_payload = None
            if parsed["vega_spec"] and not _chart_mentions_suppressed(parsed["vega_spec"]):
                chart_payload = {"vegaSpec": parsed["vega_spec"]}
            elif columns:
                # Either no agent chart, or one built on a suppressed measure.
                # Redrawing from the filtered table keeps a chart on the page
                # instead of dropping the visual entirely.
                chart = _chart_from_rows(columns, rows)
                if chart:
                    chart_payload = {"chartjs": chart}

            # The agent proposes its own follow-ups, grounded in what it just
            # queried. Prefer those over a second model call that only sees
            # the question and answer text.
            suggestions = [q for q in parsed["suggestions"]
                           if not any(t in q.lower() for t in SUPPRESSED_SUGGESTION_TERMS)][:5]
            if not suggestions:
                suggestions = followup_suggestions(question, answer_text)

            # metadata.usage already arrives in the {tokens_consumed: [...]}
            # shape that _calc_total_tokens/_calc_cost and static/js/app.js
            # read, so it passes through untouched.
            usage = parsed["usage"] or None

            reasoning_steps = parsed["thinking"] or None
            elapsed = round(time.time() - t0, 2)
            interaction_id = str(uuid.uuid4())
            now_iso = datetime.now(timezone.utc).isoformat()

            yield _sse("done", _build_chat_payload(
                interaction_id, conversation_id, answer_text, parsed["sql"],
                suggestions, elapsed, columns, rows, None, chart_payload,
                usage, reasoning_steps))

            relevance = _judge_answer_relevance(question, answer_text)
            _log_event({
                "timestamp": now_iso, "interaction_id": interaction_id,
                "type": "agent", "user": login, "question": question,
                "answer": answer_text, "sql": parsed["sql"],
                "total_tokens": _calc_total_tokens(usage),
                "cost": round(_calc_cost(usage), 5),
                "relevance_percent": relevance,
            })
            shown = relevance if relevance == 100 else None
            _append_message_to_conversation(
                login, conversation_id,
                _build_chat_message_record(
                    interaction_id, question, answer_text, now_iso, parsed["sql"],
                    elapsed, columns, rows, None, chart_payload, usage,
                    reasoning_steps, shown))
            if shown is not None:
                yield _sse("relevance", {"interaction_id": interaction_id,
                                         "relevance_percent": shown})

        except Exception as e:
            yield _sse("error", {"error": _friendly_error_message(e)})

    return Response(stream_with_context(generate()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ═══════════════════════════════════════════════════════════════════════════
# Real-subgraph view: turn the entities named in an answer back into the
# actual nodes and relationships that connect them in the Snowflake KG.
# ═══════════════════════════════════════════════════════════════════════════
# SCS.KG.KG_NODES stores one row per canonical entity with a human-readable
# LABEL, and SCS.KG.KG_EDGES joins them. That makes the label the natural
# join key back from an answer's result table: whatever the agent printed in
# a cell is looked up as a label, and whatever matches becomes a seed. No
# prefix convention or per-label key mapping is needed — the graph itself
# decides which cells are entities.
SUBGRAPH_SEED_CAP = 8      # seed entities expanded per request
SUBGRAPH_FANOUT = 6        # neighbours kept per seed, by edge weight
SUBGRAPH_NODE_CAP = 160
SUBGRAPH_EDGE_SCAN = 2000  # edges pulled back before per-seed capping

# Colour/grouping index per node type, so related entity classes stay visually
# distinct. Anything not listed falls into a shared "other" group.
NODE_TYPE_GROUPS = {
    "CUSTOMER": 0, "PART": 1, "COMMODITY": 2, "SUPPLIER": 3,
    "SUPPLIER_SITE": 4, "PRODUCT": 5, "PLANT": 6, "WAREHOUSE": 7,
    "LANE": 8, "PORT": 9, "CARRIER": 10, "COUNTRY": 11,
}
SUBGRAPH_OTHER_GROUP = 12

# Cells that can't be an entity label: too short to be distinctive, too long
# to be anything but prose, or a pure number/date the answer is reporting.
_NON_ENTITY_CELL = re.compile(r"^[\s\d.,$%+-]*$")


def _candidate_labels(columns, rows):
    """Distinct cell values from a result table that could name an entity."""
    seen, out = set(), []
    if not rows:
        return out
    for row in rows:
        for cell in row:
            if not isinstance(cell, str):
                continue
            value = cell.strip()
            if not (2 < len(value) <= 120) or _NON_ENTITY_CELL.match(value):
                continue
            key = value.upper()
            if key not in seen:
                seen.add(key)
                out.append(value)
    return out


def detect_seeds(columns, rows):
    """Result-table cells that are real nodes in the graph, most central first.

    Matching is done by the database rather than by pattern, so a cell only
    becomes a seed when an actual node carries that label. Ordering by
    PageRank means that when a table names more entities than the view can
    hold, the ones kept are the ones the graph considers most connected.
    """
    labels = _candidate_labels(columns, rows)
    if not labels:
        return []
    # Cap what goes into the IN list: a wide table can easily carry hundreds
    # of distinct cells, and the seed cap discards all but a handful anyway.
    labels = labels[:400]
    placeholders = ", ".join(["%s"] * len(labels))
    sql = (f"SELECT NODE_ID, NODE_TYPE, LABEL FROM {KG_SCHEMA}.KG_NODES "
           f"WHERE UPPER(LABEL) IN ({placeholders}) "
           f"ORDER BY PAGERANK DESC NULLS LAST LIMIT {SUBGRAPH_SEED_CAP}")
    _cols, found = sf_query(sql, tuple(l.upper() for l in labels),
                            max_rows=SUBGRAPH_SEED_CAP)
    return [{"node_id": r[0], "node_type": r[1], "label": r[2]} for r in found]


# One hop out from the seeds, in either direction, heaviest edges first.
SUBGRAPH_EDGE_SQL = """
SELECT e.EDGE_TYPE, e.WEIGHT,
       a.NODE_ID, a.NODE_TYPE, a.LABEL,
       b.NODE_ID, b.NODE_TYPE, b.LABEL
FROM {kg}.KG_EDGES e
JOIN {kg}.KG_NODES a ON a.NODE_ID = e.FROM_NODE_ID
JOIN {kg}.KG_NODES b ON b.NODE_ID = e.TO_NODE_ID
WHERE e.FROM_NODE_ID IN ({ph}) OR e.TO_NODE_ID IN ({ph})
ORDER BY e.WEIGHT DESC NULLS LAST
LIMIT {scan}
"""


def build_subgraph(columns, rows):
    """Real nodes/edges connecting the entities this answer mentions."""
    seeds = detect_seeds(columns, rows)
    if not seeds:
        return {"nodes": [], "edges": [], "truncated": False, "seeds": {}}

    seed_ids = [s["node_id"] for s in seeds]
    sql = SUBGRAPH_EDGE_SQL.format(
        kg=KG_SCHEMA, ph=", ".join(["%s"] * len(seed_ids)), scan=SUBGRAPH_EDGE_SCAN)
    _cols, edge_rows = sf_query(sql, tuple(seed_ids) * 2, max_rows=SUBGRAPH_EDGE_SCAN)

    nodes, edges, seen_edges = {}, [], set()
    # The fan-out cap is per seed, not overall: without it one hub supplier
    # with thousands of parts would crowd every other seed out of the view.
    per_seed = {nid: 0 for nid in seed_ids}
    seed_set = set(seed_ids)

    def add_node(node_id, node_type, label):
        nid = f"{node_type}:{label}"
        if nid not in nodes and len(nodes) < SUBGRAPH_NODE_CAP:
            nodes[nid] = {"data": {
                "id": nid, "label": label, "type": node_type,
                "group": NODE_TYPE_GROUPS.get(node_type, SUBGRAPH_OTHER_GROUP),
            }}
        return nid if nid in nodes else None

    for seed in seeds:
        add_node(seed["node_id"], seed["node_type"], seed["label"])

    for edge_type, _weight, a_id, a_type, a_label, b_id, b_type, b_label in edge_rows:
        # Which end anchored this edge decides whose fan-out budget it spends.
        anchor = a_id if a_id in seed_set else b_id
        if anchor in per_seed and per_seed[anchor] >= SUBGRAPH_FANOUT:
            continue
        src = add_node(a_id, a_type, a_label)
        dst = add_node(b_id, b_type, b_label)
        if not (src and dst) or src == dst:
            continue
        key = f"{src}|{edge_type}|{dst}"
        if key in seen_edges:
            continue
        seen_edges.add(key)
        edges.append({"data": {"id": f"e{len(edges)}", "source": src,
                               "target": dst, "label": edge_type}})
        if anchor in per_seed:
            per_seed[anchor] += 1
        if len(nodes) >= SUBGRAPH_NODE_CAP:
            break

    seeds_by_type = {}
    for seed in seeds:
        seeds_by_type.setdefault(seed["node_type"], []).append(seed["label"])

    return {"nodes": list(nodes.values()), "edges": edges,
            "truncated": len(nodes) >= SUBGRAPH_NODE_CAP,
            "seeds": seeds_by_type}


@app.route("/api/subgraph", methods=["POST"])
def api_subgraph():
    """Real Snowflake KG subgraph for the entities in an answer's result table."""
    body = request.get_json(silent=True) or {}
    columns = body.get("columns") or []
    rows = body.get("rows") or []
    try:
        graph = build_subgraph(columns, rows)
    except Exception as e:
        app.logger.warning("subgraph build failed: %s", e)
        return jsonify({"error": "Could not build the graph view."}), 200
    if not graph["nodes"]:
        return jsonify({"error": "No graph entities in this result."}), 200
    return jsonify(graph)


if __name__ == "__main__":
    # Port and debug come from .env so production does not need a code change.
    app.run(host="0.0.0.0",
            port=int(os.environ.get("PORT", "8000")),
            debug=os.environ.get("FLASK_DEBUG", "0") == "1")
