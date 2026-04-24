# Clinical AI RegWatch

Weekly-refreshed knowledge base of global regulatory and ethical guidance on clinical AI, with a Streamlit UI for browsing, searching, and drafting internal procedures.

## Audience

Head of Regulation & Research at a large medical center with an internal AI Center responsible for both AI procurement and AI development.

## Stack

- **Scraping:** Python (requests + BeautifulSoup), runs weekly via GitHub Actions
- **Storage:** Supabase Postgres + pgvector (semantic search)
- **LLM:** Google Gemini (classification, summaries, RAG procedure drafting, embeddings)
- **UI:** Streamlit Cloud

## Sources (initial)

| Region | Source |
|---|---|
| US | FDA — AI/ML SaMD Action Plan, AI-enabled device list, draft guidances |
| EU | EMA reflection papers + EU AI Act updates |
| UK | MHRA Software & AI as Medical Device program |
| IL | משרד הבריאות — חוזרי מנכ"ל, חוזרי רפואה |
| Global | WHO ethics & governance of AI for health |
| Standards | ISO/IEC 42001, IMDRF, NIST AI RMF |

## Local setup

1. `python -m venv .venv && .venv\Scripts\activate`
2. `pip install -r requirements.txt`
3. Copy `.env.example` → `.env` and fill credentials
4. Run `db/schema.sql` once in Supabase SQL Editor
5. `python -m pipeline.run_weekly` to populate the database
6. `streamlit run app/streamlit_app.py`

## Deployment

- **Cron:** `.github/workflows/weekly-scrape.yml` runs Sundays 22:00 UTC
- **App:** Streamlit Cloud, secrets configured for `DATABASE_URL` + `GEMINI_API_KEY`
