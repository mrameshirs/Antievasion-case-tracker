# GST Anti-Evasion Case Tracker

A Streamlit app to upload, track, search, and visualize anti-evasion GST
investigation cases approved by the Principal Commissioner (Mumbai East
Commissionerate). Case photos and the central data sheet are stored in
Dropbox, in their own folder tree separate from any other app.

## Extraction pipeline
1. Admin uploads photos (mobile browsers offer the camera as a source).
2. Photos are resized/compressed locally (`image_utils.py`) — longest side
   capped at 2000px, JPEG quality 88 — for faster OCR/upload without
   meaningfully hurting legibility.
3. **Tesseract OCR** (`ocr_utils.py`) reads the text locally, no network call.
4. The combined OCR text is sent to a **free OpenRouter text model**
   (`openrouter_utils.py`) which structures it into GSTIN(s), trade name(s),
   case summary, suggested category, and approval date. Falls through a list
   of free models if one is unavailable/rate-limited.
5. Admin reviews and corrects everything in an editable form before it's
   ever saved — this is the single point of quality control, since OCR +
   free LLMs can misread handwriting.
6. On submit, GSTIN(s) are validated against the standard 15-character GSTIN
   pattern and the Investigation Group is checked against A–I; the row is
   only saved once all fields pass validation.

## Multiple GSTINs / trade names per case
One case FILE (one `Serial_No`) can involve more than one taxpayer. GSTINs
and trade names are entered as comma/semicolon-separated lists, kept in the
same order (Nth GSTIN ↔ Nth trade name), and stored as `"; "`-joined text in
the `GSTINs` / `Trade_Names` columns.

## Files
- `app.py` — main entry point, login gate, Dropbox init, sidebar navigation
- `config.py` — configuration: credentials, Dropbox paths, categories,
  groups (A–I), statuses, GSTIN regex, OpenRouter free text-model list,
  extraction prompt
- `validators.py` — GSTIN regex validation, investigation-group validation,
  comma/semicolon list parsing
- `image_utils.py` — photo resize/compression before OCR and storage
- `ocr_utils.py` — Tesseract OCR wrapper
- `models.py` — pydantic schemas for the extracted / stored case data
- `dropbox_utils.py` — Dropbox client, folder/file helpers, read/write the
  central Excel sheet, serial-number generation, row append/update
- `openrouter_utils.py` — sends OCR'd text (never images) to free OpenRouter
  text models and parses the returned JSON, with automatic model fallback
- `ui_login.py` — login screen
- `ui_upload.py` — Module 1: photos → compress → OCR → AI structuring →
  review & edit → validate → submit to Dropbox
- `ui_view_search.py` — Module 2: view, filter, search the case sheet, and
  view uploaded photos per case on demand
- `ui_visualize.py` — Module 3: date-wise, group-wise, category-wise and
  status-wise charts
- `ui_edit.py` — Module 4 (Admin only): correct any row, with the same
  GSTIN/group validation as upload

## Required `.streamlit/secrets.toml`

```toml
# Dropbox (create an app at https://www.dropbox.com/developers/apps,
# generate a refresh token with scopes files.content.write / files.content.read / sharing.write)
dropbox_app_key = "..."
dropbox_app_secret = "..."
dropbox_refresh_token = "..."

# OpenRouter (https://openrouter.ai/keys) — free tier is fine for the
# models listed in config.py
openrouter_api_key = "..."

# Login passwords (override the defaults in config.py)
admin_password = "choose-a-strong-password"
viewer1_password = "choose-a-strong-password"
```

## System dependency: Tesseract

Tesseract OCR must be installed as a system binary (it's not a pure-Python
package). `packages.txt` (`tesseract-ocr`) is included so this installs
automatically on Streamlit Community Cloud. For local development:

```bash
# Debian/Ubuntu
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract
```

## Roles
- **Admin** (`admin`): Upload Case, View & Search, Visualizations, Edit Cases
- **Viewer** (`viewer1`): View & Search, Visualizations (read-only)

Add more viewer accounts by extending `USER_CREDENTIALS` / `USER_ROLES` in
`config.py`.

## Notes
- **Handwriting**: Tesseract is a classical OCR engine and is weaker on
  handwriting than the vision-LLM approach would have been. Since every
  upload is manually reviewed before saving, this is treated as an
  acceptable tradeoff for speed/cost — but expect to hand-correct
  handwritten dates/notes more often.
- **Dropbox folder**: everything lives under `/GST_AntiEvasion_Tracker`
  (`config.DROPBOX_ROOT_PATH`), a folder tree created on first run and kept
  entirely separate from any other app's Dropbox data.
- **OpenRouter model slugs**: free-tier slugs occasionally change on
  OpenRouter's end. If extraction starts failing on every model, check
  https://openrouter.ai/models and update `OPENROUTER_MODEL_ALIASES` in
  `config.py`.
