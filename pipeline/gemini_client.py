import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

_API_KEY = os.environ.get("GEMINI_API_KEY")
if _API_KEY:
    genai.configure(api_key=_API_KEY)

CHAT_MODEL = "gemini-2.5-flash"
EMBED_MODEL = "models/gemini-embedding-001"
EMBED_DIM = 768  # gemini-embedding-001 supports MRL — we request 768 explicitly to match pgvector schema
