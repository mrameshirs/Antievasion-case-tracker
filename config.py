# config.py
import streamlit as st

# --- Dropbox Configuration (same OAuth refresh-token pattern as before) ---
DROPBOX_APP_KEY = st.secrets.get("dropbox_app_key", "")
DROPBOX_APP_SECRET = st.secrets.get("dropbox_app_secret", "")
DROPBOX_REFRESH_TOKEN = st.secrets.get("dropbox_refresh_token", "")

# --- OpenRouter Configuration ---
OPENROUTER_API_KEY = st.secrets.get("openrouter_api_key", "")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Free TEXT (non-vision) OpenRouter models used to structure the OCR text.
# OCR is done locally by Tesseract; these models only ever see plain text.
OPENROUTER_MODEL_ALIASES = {
    "gemma-4-26b":"google/gemma-4-26b-a4b-it:free",
    "gemma-4-31b":"google/gemma-4-31b-it:free",
    "nemotron-3-utlra":"nvidia/nemotron-3-ultra-550b-a55b:free",
    "gpt-oss":"openai/gpt-oss-20b:free"
    
    
    # "llama-3.3-70b": "meta-llama/llama-3.3-70b-instruct:free",
    # "qwen-2.5-72b": "qwen/qwen-2.5-72b-instruct:free",
    # "mistral-small": "mistralai/mistral-small-3.1-24b-instruct:free",
    # "gemma-27b": "google/gemma-3-27b-it:free",
    # "deepseek-chat": "deepseek/deepseek-chat:free",
    # "gemma-12b": "google/gemma-3-12b-it:free",
}
# Order in which models are tried (first = preferred). Free models can be
# rate-limited / flaky, so the caller falls through this list on failure.
OPENROUTER_MODEL_FALLBACK_ORDER = [
    "gemma-4-26b",
    "gemma-4-31b",
    "nemotron-3-utlra",
    "gpt-oss"]
# NOTE: OpenRouter's exact free-model slugs change over time. If a call
# fails with a 404/"model not found" error, check https://openrouter.ai/models
# and update the aliases above.

# --- Centralized Folders and Files in Dropbox ---
# Deliberately a NEW, separate folder tree - not shared with any other app
# (e.g. the earlier e-MCM app used "/e-MCM_App"). Everything below is
# created automatically on first run if it doesn't already exist.
DROPBOX_ROOT_PATH = "/GST_AntiEvasion_Tracker"
CASE_PHOTOS_PATH = f"{DROPBOX_ROOT_PATH}/Case_Photos"
CASES_DATA_PATH = f"{DROPBOX_ROOT_PATH}/anti_evasion_cases.xlsx"
LOG_FILE_PATH = f"{DROPBOX_ROOT_PATH}/log_sheet.xlsx"

# --- User Credentials & Roles ---
# Admin: can upload new cases and edit the data sheet.
# Viewer: read-only access to the View/Search and Visualization modules.
USER_CREDENTIALS = {
    "admin": st.secrets.get("admin_password", "admin_password"),
    "viewer1": st.secrets.get("viewer1_password", "viewer1_password"),
}
USER_ROLES = {
    "admin": "Admin",
    "viewer1": "Viewer",
}

# --- Case Classification ---
# Investigation group must be exactly one of these - strictly A through I,
# nothing else. Enforced both in the UI (dropdown) and in validators.py.
INVESTIGATION_GROUPS = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]

CASE_CATEGORIES = [
    "Fake ITC",
    "Issue-based",
    "Reference from Audit",
    "Others",
]

STATUS_OPTIONS = [
    "Investigation Initiated",
    "Summons Issued",
    "Under Investigation",
    "Show Cause Notice Issued",
    "Adjudicated",
    "Closed",
]

# --- GSTIN validation ---
# Standard 15-character GSTIN pattern: 2-digit state code, 10-char PAN,
# 1-char entity code, 'Z' by default, 1 checksum alphanumeric character.
GSTIN_REGEX = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'

# --- Data sheet column order ---
# One case file (Serial_No) can involve MORE THAN ONE GSTIN / trade name
# (e.g. multiple linked entities investigated under a single approved
# case). GSTINs and Trade_Names are stored as "; "-separated lists in a
# single cell, in the same order, so the Nth GSTIN corresponds to the Nth
# trade name.
DATA_SHEET_COLUMNS = [
    "Serial_No",
    "GSTINs",
    "Trade_Names",
    "Case_Summary",
    "Category",
    "Investigation_Group",
    "Status",
    "Date_of_Approval",
    "Uploaded_By",
    "Uploaded_On",
    "Photo_Links",
]

# --- LLM extraction prompt (operates on OCR'd plain text, no images) ---
CASE_EXTRACTION_SYSTEM_PROMPT = """
You are an expert assistant for a GST (Goods and Services Tax) Anti-Evasion
wing in India. Below is raw OCR text extracted from 1 or more photographs of
a page (or pages) from an investigation-approval file / office note approved
by the Principal Commissioner. The OCR text may contain errors, especially
around handwritten portions - use context to make reasonable corrections
where obvious (e.g. fixing an obviously mis-OCR'd digit in a date), but do
not invent information that isn't implied by the text.

There may be MORE THAN ONE taxpayer (GSTIN + trade name) named in the same
case file. Extract all of them, keeping GSTINs and trade names in the same
order so the Nth GSTIN corresponds to the Nth trade name.

Respond with ONLY a single valid JSON object (no markdown fences, no extra
text) with exactly these keys:

{
  "gstins": ["list of GSTIN strings found, e.g. ['27AAAFP6015C1ZQ'], empty list if none found"],
  "trade_names": ["list of trade/legal names, same order and same length as gstins where possible"],
  "case_summary": "a concise 2-4 sentence summary of the nature of the case / allegation, in your own words",
  "category_suggestion": "your best guess at ONE of: 'Fake ITC', 'Issue-based', 'Reference from Audit', 'Others'",
  "date_of_approval": "the date on which the Principal Commissioner approved the investigation, in YYYY-MM-DD format if determinable, else null"
}

Rules:
- gstins and trade_names must be JSON arrays (use empty arrays if nothing found), not comma-separated strings.
- Do not invent a GSTIN; only extract it if it plausibly appears in the OCR text.
- category_suggestion must be exactly one of the four listed options.
- Output must be valid JSON and nothing else.

OCR TEXT:
---
{ocr_text}
---
"""
