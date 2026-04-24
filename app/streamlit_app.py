"""Clinical AI RegWatch — Streamlit UI (Hebrew, RTL, mobile-friendly)."""
from __future__ import annotations
import hmac
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.connection import connect  # noqa: E402
from pipeline.embed import embed_query  # noqa: E402
import google.generativeai as genai  # noqa: E402
from pipeline.gemini_client import CHAT_MODEL  # noqa: E402

st.set_page_config(
    page_title="Clinical AI RegWatch",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# RTL + mobile-friendly CSS — aggressive overrides for Streamlit's default LTR layout
st.markdown("""
<style>
/* Use a Hebrew-friendly font stack everywhere */
html, body, .stApp, [class*="css"] {
    font-family: 'Segoe UI', 'Arial Hebrew', 'David', 'Frank Ruehl CLM', system-ui, sans-serif;
}

/* Force RTL on the entire app */
html, body, .stApp, .main, section[data-testid="stAppViewContainer"],
section[data-testid="stMain"], div[data-testid="stMainBlockContainer"] {
    direction: rtl !important;
}

/* All markdown content: RTL, right-aligned, but use plaintext bidi
   so mixed Hebrew/English (and citations like [1]) flow correctly per-paragraph */
.stMarkdown, .stMarkdown *,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] *,
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {
    direction: rtl !important;
    text-align: right !important;
    unicode-bidi: plaintext;
}

/* Headings */
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4,
[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {
    text-align: right !important;
    unicode-bidi: plaintext;
}

/* Lists: bullets/numbers on the right side */
.stMarkdown ul, .stMarkdown ol { padding-right: 1.5rem; padding-left: 0; }
.stMarkdown li { text-align: right; unicode-bidi: plaintext; }

/* Inputs: type RTL by default */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {
    direction: rtl !important;
    text-align: right !important;
}

/* Tabs: keep tab order natural for RTL readers (first declared tab on the right) */
.stTabs [data-baseweb="tab-list"] { direction: rtl; }

/* Buttons: align to the right */
.stButton { text-align: right; }

/* Expanders: header text RTL */
[data-testid="stExpander"] summary { direction: rtl; text-align: right; }
[data-testid="stExpander"] [data-testid="stMarkdownContainer"] { direction: rtl; }

/* Sliders/multiselect labels stay RTL */
.stSlider label, .stMultiSelect label, .stRadio label, .stSelectbox label {
    direction: rtl !important; text-align: right !important;
}

/* Code blocks, URLs, pre: stay LTR (they're never Hebrew) */
code, pre, kbd, .stCode {
    direction: ltr !important;
    text-align: left !important;
    unicode-bidi: isolate;
}
.stMarkdown a { unicode-bidi: plaintext; }

/* Drafted procedure card: high contrast so text isn't washed out inside expanders */
.draft-card {
    background: #ffffff;
    color: #0d1117;
    border: 1px solid #d0d7de;
    border-right: 4px solid #1f6feb;
    border-radius: 8px;
    padding: 1.25rem 1.5rem;
    margin: 1rem 0;
    direction: rtl;
    text-align: right;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    line-height: 1.6;
}
.draft-card * { color: #0d1117 !important; }
.draft-card h1, .draft-card h2, .draft-card h3, .draft-card h4 {
    margin-top: 1.1rem;
    color: #0d1117 !important;
    font-weight: 700;
}
.draft-card strong { color: #000 !important; font-weight: 700; }
.draft-card a { color: #0969da !important; text-decoration: underline; }
.draft-card p, .draft-card li { color: #0d1117 !important; font-size: 1rem; }
.draft-card hr { border-color: #d0d7de; }

/* Source card */
.source-item {
    border-right: 3px solid #1f6feb;
    background: #f8f9fb;
    padding: 0.6rem 0.9rem;
    margin: 0.4rem 0;
    border-radius: 6px;
    direction: rtl;
    text-align: right;
    unicode-bidi: plaintext;
}

/* Mobile tweaks */
@media (max-width: 768px) {
    .main .block-container, [data-testid="stMainBlockContainer"] {
        padding: 0.6rem 0.6rem 4rem 0.6rem;
    }
    h1 { font-size: 1.35rem; }
    h2 { font-size: 1.1rem; }
    h3 { font-size: 0.95rem; }
    .stTextArea textarea { min-height: 110px; font-size: 1rem; }
    .stTabs [data-baseweb="tab"] { padding: 0.4rem 0.6rem; font-size: 0.85rem; }
    .stMarkdown p { font-size: 0.95rem; line-height: 1.55; }
    .draft-card { padding: 1rem; }
}
</style>
""", unsafe_allow_html=True)

CATEGORIES_EN = ["Implementation", "Monitoring", "Validation", "Ethics", "Security", "Other"]
CATEGORY_HE = {
    "Implementation": "יישום",
    "Monitoring": "ניטור",
    "Validation": "וולידציה",
    "Ethics": "אתיקה",
    "Security": "אבטחה",
    "Other": "אחר",
    # legacy labels still in DB
    "Development": "פיתוח",
    "Clinical Validation": "וולידציה קלינית",
}
REGIONS_EN = ["US", "EU", "IL", "UK", "Global"]
REGION_HE = {"US": "ארה\"ב", "EU": "אירופה", "IL": "ישראל", "UK": "בריטניה", "Global": "גלובלי", "": "—"}

SOURCE_LABELS = {
    "fda": "FDA (ארה\"ב)",
    "who": "WHO (גלובלי)",
    "ema": "EMA (אירופה)",
    "mhra": "MHRA (בריטניה)",
    "stanford_aimi": "Stanford AIMI",
    "mgb_aim": "MGB AiM (Mass General Brigham)",
    "moh_il": "משרד הבריאות (ישראל)",
}

DEFAULT_DRAFT_PROMPT = """אתה מנסח נוהל פנימי עבור מרכז ה-AI במרכז רפואי גדול.
המוקד של המרכז הוא **יישום, ניטור ו-וולידציה** של כלי בינה מלאכותית קליניים — לא רכש או הערכת ספקים.
הנהלים אמורים לכסות כיצד המרכז מטמיע, מנטר ומאמת כלי AI המשמשים בטיפול בחולים.

נסח נוהל המתייחס לבקשת המשתמש למטה. בסס כל דרישה במקורות שאוחזרו וצטט אותם בתוך הטקסט בסוגריים מרובעים: [1], [2] וכו'.
אם המקורות אינם מכסים נושא שהבקשה מתייחסת אליו — ציין זאת במפורש במקום להמציא דרישות.
השתמש בסעיפים ברורים: מטרה, היקף, הגדרות, אחריות, שלבי הנוהל, מקורות.
"""


@st.cache_resource
def get_conn():
    return connect(autocommit=True)


@st.cache_resource
def get_model():
    return genai.GenerativeModel(CHAT_MODEL)


def fetch_recent(days: int = 7):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    sql = """
        select id, source, url, title, summary, why_care, category, region,
               published_at, scraped_at, last_changed_at
          from documents
         where scraped_at >= %s
            or last_changed_at >= %s
         order by category, coalesce(last_changed_at, scraped_at) desc
    """
    with get_conn().cursor() as cur:
        cur.execute(sql, (cutoff, cutoff))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def _freshness_badge(d: dict, days: int) -> str:
    """Return 🆕 / 🔄 / '' based on scraped_at vs last_changed_at."""
    now = datetime.now(timezone.utc)
    cutoff = timedelta(days=days)
    scraped = d.get("scraped_at")
    changed = d.get("last_changed_at")
    if scraped and (now - scraped) <= cutoff:
        return " 🆕"
    if changed and (now - changed) <= cutoff and scraped and (now - scraped) > cutoff:
        return " 🔄"
    return ""


def semantic_search(query: str, limit: int = 10, category: str | None = None, region: str | None = None):
    qvec = embed_query(query)
    where = []
    extra_params: list = []
    if category:
        where.append("category = %s")
        extra_params.append(category)
    if region:
        where.append("region = %s")
        extra_params.append(region)
    where_sql = ("where " + " and ".join(where)) if where else ""
    sql = f"""
        select id, source, url, title, summary, why_care, category, region,
               published_at, 1 - (embedding <=> %s::vector) as similarity
          from documents
          {where_sql}
         order by embedding <=> %s::vector
         limit %s
    """
    params = [qvec, *extra_params, qvec, limit]
    with get_conn().cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def draft_procedure(user_request: str, retrieved: list[dict], language_label: str, system_prompt: str) -> str:
    sources_block = "\n\n".join(
        f"[{i+1}] {d['title']} ({d['source']}, {d['region']})\nURL: {d['url']}\nSUMMARY: {d.get('summary') or ''}"
        for i, d in enumerate(retrieved)
    )
    lang_directive = (
        "כתוב את התשובה כולה בעברית. שמור על מספרי הציטוטים [1], [2]... כפי שהם."
        if language_label == "עברית"
        else "Write the entire response in English. Preserve citation numbers [1], [2]... as-is."
    )
    full_prompt = f"""{system_prompt}

{lang_directive}

USER REQUEST:
{user_request}

RETRIEVED REGULATORY SOURCES:
{sources_block}
"""
    resp = get_model().generate_content(full_prompt)
    return resp.text


def save_draft(user_request: str, system_prompt: str, language: str, draft_text: str, source_ids: list[int]) -> int:
    sql = """
        insert into drafts (user_request, system_prompt, language, draft_text, source_ids)
        values (%s, %s, %s, %s, %s)
        returning id
    """
    with get_conn().cursor() as cur:
        cur.execute(sql, (user_request, system_prompt, language, draft_text, source_ids))
        return cur.fetchone()[0]


def update_draft(draft_id: int, language: str, draft_text: str) -> None:
    sql = "update drafts set language = %s, draft_text = %s where id = %s"
    with get_conn().cursor() as cur:
        cur.execute(sql, (language, draft_text, draft_id))


def list_drafts(limit: int = 50) -> list[dict]:
    sql = """
        select id, user_request, language, draft_text, source_ids, created_at
          from drafts
         order by created_at desc
         limit %s
    """
    with get_conn().cursor() as cur:
        cur.execute(sql, (limit,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_draft_sources(source_ids: list[int]) -> list[dict]:
    if not source_ids:
        return []
    sql = """
        select id, source, url, title, summary, category, region
          from documents
         where id = any(%s)
    """
    with get_conn().cursor() as cur:
        cur.execute(sql, (source_ids,))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    by_id = {r["id"]: r for r in rows}
    return [by_id[i] for i in source_ids if i in by_id]


def translate_text(text: str, target_language_label: str) -> str:
    target = "Hebrew" if target_language_label == "עברית" else "English"
    prompt = f"""Translate the following document to {target}.
Preserve markdown formatting, headings, bullet structure, and inline citation numbers like [1], [2] exactly.
Do not add commentary or notes.

DOCUMENT:
{text}
"""
    resp = get_model().generate_content(prompt)
    return resp.text


# --- Password gate ---
def _get_app_password() -> str:
    return st.secrets.get("APP_PASSWORD", "") if hasattr(st, "secrets") and "APP_PASSWORD" in (st.secrets or {}) else os.environ.get("APP_PASSWORD", "")


def _check_password() -> bool:
    expected = _get_app_password()
    if not expected:
        return True  # no password configured -> open access (dev fallback)
    if st.session_state.get("auth_ok"):
        return True

    st.title("Clinical AI RegWatch")
    st.markdown("##### נדרשת סיסמה לכניסה")

    with st.form("login_form", clear_on_submit=False):
        pw = st.text_input("סיסמה", type="password")
        submit = st.form_submit_button("כניסה", type="primary", use_container_width=True)
        if submit:
            if hmac.compare_digest(pw, expected):
                st.session_state.auth_ok = True
                st.rerun()
            else:
                st.session_state.auth_ok = False

    if st.session_state.get("auth_ok") is False:
        st.error("סיסמה שגויה")
    return False


if not _check_password():
    st.stop()

# --- Header ---
st.title("Clinical AI RegWatch")
st.caption("מאגר עדכני של רגולציית AI קלינית גלובלית — לראש תחום רגולציה ומחקר במרכז רפואי")

# --- Session state init ---
if "draft" not in st.session_state:
    st.session_state.draft = None
    st.session_state.draft_lang = None
    st.session_state.draft_id = None
    st.session_state.retrieved = []

tab_draft, tab_brief, tab_search, tab_history = st.tabs(
    ["📝 ניסוח נוהל", "🗞️ סיכום שבועי", "🔍 חיפוש", "🗂️ היסטוריה"]
)

# --- Tab 1: Procedure Drafter ---
with tab_draft:
    st.subheader("ניסוח נוהל מבוסס מקורות")
    st.markdown(
        "תאר את הנוהל שברצונך לנסח. המערכת תאחזר את המקורות הרגולטוריים הרלוונטיים ביותר ותנסח טיוטה עם ציטוטים בתוך הטקסט."
    )

    user_prompt = st.text_area(
        "תיאור הבקשה",
        placeholder='לדוגמה: "נוהל למרכז ה-AI לטיפול ב-Drift של מודל אבחון רדיולוגי לאחר עליה לאוויר, לפי הנחיות FDA ו-WHO עדכניות."',
        height=120,
    )

    col1, col2 = st.columns(2)
    language = col1.radio("שפת הניסוח", ["עברית", "English"], horizontal=True, index=0)
    n_sources = col2.slider("מספר מקורות לאחזור", 3, 20, 8)

    with st.expander("עריכת הוראות הניסוח (system prompt)"):
        custom_prompt = st.text_area(
            "ההוראות שמועברות ל-Gemini לפני בקשת המשתמש והמקורות:",
            value=DEFAULT_DRAFT_PROMPT,
            height=240,
            key="custom_prompt",
        )

    if st.button("✨ נסח נוהל", type="primary"):
        if not user_prompt.strip():
            st.warning("יש להזין תיאור בקשה לפני הניסוח.")
            st.stop()
        with st.spinner("מאחזר מקורות..."):
            try:
                retrieved = semantic_search(user_prompt, limit=n_sources)
            except Exception as e:
                st.error(f"כשל באחזור: {e}")
                retrieved = []
        if not retrieved:
            st.warning("לא אוחזרו מקורות — הניסוח לא יהיה מבוסס. הרץ את הסקרייפר תחילה.")
        with st.spinner("מנסח טיוטה..."):
            try:
                draft = draft_procedure(user_prompt, retrieved, language, custom_prompt)
            except Exception as e:
                st.error(f"כשל בניסוח: {e}")
                draft = ""
        if draft:
            st.session_state.draft = draft
            st.session_state.draft_lang = language
            st.session_state.retrieved = retrieved
            try:
                st.session_state.draft_id = save_draft(
                    user_prompt, custom_prompt, language, draft, [d["id"] for d in retrieved]
                )
            except Exception as e:
                st.warning(f"לא נשמרה היסטוריה: {e}")
                st.session_state.draft_id = None

    if st.session_state.draft:
        # Translation toolbar (right above the draft so it's the first thing the user sees)
        current_lang = st.session_state.draft_lang
        target_lang = "English" if current_lang == "עברית" else "עברית"
        toolbar = st.columns([2, 2, 6])
        if toolbar[0].button(f"🌐 תרגם ל-{target_lang}", use_container_width=True):
            with st.spinner("מתרגם..."):
                try:
                    translated = translate_text(st.session_state.draft, target_lang)
                    st.session_state.draft = translated
                    st.session_state.draft_lang = target_lang
                    if st.session_state.draft_id:
                        try:
                            update_draft(st.session_state.draft_id, target_lang, translated)
                        except Exception:
                            pass
                    st.rerun()
                except Exception as e:
                    st.error(f"כשל בתרגום: {e}")
        if toolbar[1].button("🗑️ נקה", use_container_width=True):
            st.session_state.draft = None
            st.session_state.draft_lang = None
            st.session_state.draft_id = None
            st.session_state.retrieved = []
            st.rerun()

        st.markdown(
            f'<div class="draft-card">\n\n{st.session_state.draft}\n\n</div>',
            unsafe_allow_html=True,
        )

        # Sources used
        st.divider()
        st.subheader("מקורות שאוחזרו")
        for i, d in enumerate(st.session_state.retrieved, 1):
            cat_he = CATEGORY_HE.get(d["category"] or "Other", d["category"] or "אחר")
            reg_he = REGION_HE.get(d["region"] or "", d["region"] or "—")
            summary = d.get("summary") or ""
            st.markdown(
                f'<div class="source-item">'
                f'<strong>[{i}]</strong> <a href="{d["url"]}" target="_blank">{d["title"]}</a>'
                f'<br><small>{d["source"]} · {reg_he} · {cat_he}</small>'
                + (f'<br><span style="color:#555;font-size:0.9em">{summary}</span>' if summary else '')
                + '</div>',
                unsafe_allow_html=True,
            )

# --- Tab 2: Weekly Briefing ---
with tab_brief:
    col_days, col_src = st.columns([1, 2])
    days = col_days.slider("הצג מסמכים שנאספו בימים האחרונים", 1, 30, 7)

    available_sources = sorted(SOURCE_LABELS.keys())
    selected_source_labels = col_src.multiselect(
        "סנן לפי מקור",
        options=[SOURCE_LABELS[s] for s in available_sources],
        default=[SOURCE_LABELS[s] for s in available_sources],
    )
    label_to_source = {v: k for k, v in SOURCE_LABELS.items()}
    selected_sources = {label_to_source[lbl] for lbl in selected_source_labels}

    try:
        docs = fetch_recent(days)
    except Exception as e:
        st.error(f"שגיאת מסד נתונים: {e}")
        docs = []

    docs = [d for d in docs if d["source"] in selected_sources]

    if not docs:
        st.info("אין מסמכים לתצוגה (אין התאמה לסינון, או שהמאגר ריק).")
    else:
        by_cat: dict[str, list[dict]] = {}
        for d in docs:
            by_cat.setdefault(d["category"] or "Other", []).append(d)
        for cat in CATEGORIES_EN:
            items = by_cat.get(cat, [])
            if not items:
                continue
            st.subheader(f"{CATEGORY_HE.get(cat, cat)} ({len(items)})")
            for d in items:
                reg_he = REGION_HE.get(d["region"] or "", d["region"] or "—")
                badge = _freshness_badge(d, days)
                with st.expander(f"[{reg_he}] {d['title']}{badge}"):
                    if d.get("why_care"):
                        st.markdown(f"**למה זה חשוב:** {d['why_care']}")
                    st.write(d.get("summary") or "_(אין סיכום)_")
                    meta_bits = [f"מקור: {d['source']}", f"נאסף: {d['scraped_at']:%Y-%m-%d}"]
                    if d.get("last_changed_at") and d.get("scraped_at") and d["last_changed_at"] > d["scraped_at"]:
                        meta_bits.append(f"עודכן: {d['last_changed_at']:%Y-%m-%d}")
                    st.caption(" | ".join(meta_bits))
                    if d.get("url"):
                        st.markdown(f"[פתח מקור]({d['url']})")

# --- Tab 3: Search ---
with tab_search:
    q = st.text_input("חיפוש סמנטי במאגר", placeholder="לדוגמה: ניטור post-market של כלי AI אבחוני")
    col1, col2, col3 = st.columns(3)
    cat_filter_he = col1.selectbox("קטגוריה", ["(הכל)"] + [CATEGORY_HE[c] for c in CATEGORIES_EN])
    reg_filter_he = col2.selectbox("אזור", ["(הכל)"] + [REGION_HE[r] for r in REGIONS_EN])
    limit = col3.slider("תוצאות", 5, 30, 10)

    cat_filter = None
    if cat_filter_he != "(הכל)":
        cat_filter = next((k for k, v in CATEGORY_HE.items() if v == cat_filter_he), None)
    reg_filter = None
    if reg_filter_he != "(הכל)":
        reg_filter = next((k for k, v in REGION_HE.items() if v == reg_filter_he and k), None)

    if q:
        try:
            results = semantic_search(q, limit=limit, category=cat_filter, region=reg_filter)
        except Exception as e:
            st.error(f"חיפוש נכשל: {e}")
            results = []
        for r in results:
            sim = r.get("similarity", 0) or 0
            reg_he = REGION_HE.get(r["region"] or "", r["region"] or "—")
            cat_he = CATEGORY_HE.get(r["category"] or "Other", r["category"] or "אחר")
            st.markdown(f"**[{reg_he}] {r['title']}** — דמיון: {sim:.2f}")
            st.caption(f"{cat_he} | {r['source']}")
            st.write(r.get("summary") or "_(אין סיכום)_")
            if r.get("url"):
                st.markdown(f"[פתח מקור]({r['url']})")
            st.divider()

# --- Tab 4: History ---
with tab_history:
    st.subheader("היסטוריית טיוטות")
    st.caption("כל טיוטה שנוסחה נשמרת כאן. לחץ כדי להציג מחדש או להעתיק.")
    try:
        drafts = list_drafts(limit=100)
    except Exception as e:
        st.error(f"שגיאה בטעינת ההיסטוריה: {e}")
        drafts = []

    if not drafts:
        st.info("עוד אין טיוטות שמורות. נסח נוהל בלשונית 'ניסוח נוהל' והוא יופיע כאן.")
    else:
        for d in drafts:
            preview = (d["user_request"] or "")[:120].replace("\n", " ")
            label = f"[{d['created_at']:%Y-%m-%d %H:%M}] · {d['language']} · {preview}"
            with st.expander(label):
                st.markdown(f"**בקשה מקורית:**")
                st.write(d["user_request"])
                st.markdown("**טיוטה:**")
                st.markdown(
                    f'<div class="draft-card">\n\n{d["draft_text"]}\n\n</div>',
                    unsafe_allow_html=True,
                )
                src_docs = get_draft_sources(d.get("source_ids") or [])
                if src_docs:
                    st.markdown("**מקורות שאוחזרו אז:**")
                    for i, s in enumerate(src_docs, 1):
                        st.markdown(f"[{i}] [{s['title']}]({s['url']}) — {s['source']}")
                if st.button(f"⬆️ טען לטיוטה הפעילה", key=f"load-{d['id']}"):
                    st.session_state.draft = d["draft_text"]
                    st.session_state.draft_lang = d["language"]
                    st.session_state.draft_id = d["id"]
                    st.session_state.retrieved = src_docs
                    st.success("נטען. עבור ללשונית 'ניסוח נוהל'.")
