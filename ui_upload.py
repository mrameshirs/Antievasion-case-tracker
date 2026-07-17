# ui_upload.py
from datetime import datetime, date

import streamlit as st

from config import (
    CASE_PHOTOS_PATH, CASES_DATA_PATH, INVESTIGATION_GROUPS,
    CASE_CATEGORIES, STATUS_OPTIONS, OPENROUTER_MODEL_ALIASES
)
from dropbox_utils import (
    create_folder, upload_new_file, get_next_serial_no, append_case_row
)
from image_utils import compress_image
from ocr_utils import extract_text_from_images
from openrouter_utils import extract_case_fields_from_text
from validators import validate_gstins, validate_investigation_group


def _reset_upload_state():
    for key in ["extracted_data", "extraction_model_used", "case_photo_bytes", "ocr_text"]:
        if key in st.session_state:
            del st.session_state[key]


def upload_case_dashboard(dbx):
    st.title("📤 Upload New Case")
    st.caption(
        "Upload photos of the approved investigation file. Text is read locally "
        "with an OCR engine, then structured by a free OpenRouter model for your review."
    )

    if "extracted_data" not in st.session_state:
        st.session_state.extracted_data = None

    # --- Step 1: capture / upload photos ---
    st.markdown("### Step 1 — Case Photos")
    uploaded_files = st.file_uploader(
        "Take photos with your camera, or select from gallery",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="case_photo_uploader"
    )

    model_choice = st.selectbox(
        "LLM model (free OpenRouter text model — first choice tried; others used as fallback)",
        options=list(OPENROUTER_MODEL_ALIASES.keys()),
        index=0
    )

    if uploaded_files:
        cols = st.columns(min(len(uploaded_files), 3))
        compressed_bytes_list = []
        for i, f in enumerate(uploaded_files):
            compressed = compress_image(f.getvalue())
            compressed_bytes_list.append((f.name, compressed))
            with cols[i % 3]:
                st.image(compressed, caption=f.name, use_container_width=True)

        if st.button("🔎 Extract Case Details (OCR + AI)", type="primary"):
            st.session_state.case_photo_bytes = [
                (name, content, "image/jpeg") for name, content in compressed_bytes_list
            ]
            with st.spinner("Running OCR on the photo(s)..."):
                ocr_text = extract_text_from_images([c for _, c in compressed_bytes_list])
                st.session_state.ocr_text = ocr_text

            with st.spinner("Structuring the extracted text with AI..."):
                parsed, model_used, error = extract_case_fields_from_text(
                    ocr_text, preferred_model=model_choice
                )
            if parsed is None:
                st.error(f"Extraction failed on all models. Last error: {error}")
            else:
                st.session_state.extracted_data = parsed
                st.session_state.extraction_model_used = model_used
                st.success(f"Extracted using model: {model_used}")

    if st.session_state.get("ocr_text"):
        with st.expander("View raw OCR text (for reference / troubleshooting)"):
            st.text(st.session_state.ocr_text)

    st.markdown("---")

    # --- Step 2: review & edit ---
    if st.session_state.extracted_data is not None:
        st.markdown("### Step 2 — Review & Edit Extracted Details")
        st.caption("This entry is only saved after you review and submit it below — please correct any OCR/AI errors.")
        data = st.session_state.extracted_data

        with st.form("review_case_form"):
            gstins_default = ", ".join(data.get("gstins") or [])
            trade_names_default = ", ".join(data.get("trade_names") or [])

            gstins_raw = st.text_input(
                "GSTIN(s) — separate multiple with a comma or semicolon", value=gstins_default
            )
            trade_names_raw = st.text_input(
                "Trade Name(s) — same order as GSTINs above, comma/semicolon separated",
                value=trade_names_default
            )
            case_summary = st.text_area("Case Summary", value=data.get("case_summary") or "", height=120)

            suggested_category = data.get("category_suggestion")
            cat_index = CASE_CATEGORIES.index(suggested_category) if suggested_category in CASE_CATEGORIES else 0
            category = st.selectbox("Category", options=CASE_CATEGORIES, index=cat_index)

            col1, col2 = st.columns(2)
            with col1:
                investigation_group = st.selectbox("Investigation Group (A–I only)", options=INVESTIGATION_GROUPS)
            with col2:
                status = st.selectbox("Status of Investigation", options=STATUS_OPTIONS)

            date_str = data.get("date_of_approval")
            try:
                default_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
            except ValueError:
                default_date = date.today()
            date_of_approval = st.date_input("Date of Approval by Principal Commissioner", value=default_date)

            submitted = st.form_submit_button("✅ Submit Case", type="primary")

            if submitted:
                valid_gstins, invalid_gstins = validate_gstins(gstins_raw)
                trade_names_list = [t.strip() for t in trade_names_raw.replace(";", ",").split(",") if t.strip()]

                errors = []
                if invalid_gstins:
                    errors.append(
                        "The following GSTIN(s) don't match the required 15-character format and must be "
                        f"corrected before saving: {', '.join(invalid_gstins)}"
                    )
                if not valid_gstins:
                    errors.append("At least one valid GSTIN is required.")
                if not trade_names_list:
                    errors.append("At least one Trade Name is required.")
                if not validate_investigation_group(investigation_group):
                    errors.append("Investigation Group must be one of A–I.")

                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    with st.spinner("Saving case and uploading photos..."):
                        serial_no = get_next_serial_no(dbx, CASES_DATA_PATH)
                        case_folder = f"{CASE_PHOTOS_PATH}/Case_{serial_no}"
                        create_folder(dbx, case_folder)

                        photo_links = []
                        for name, content, _mime in st.session_state.get("case_photo_bytes", []):
                            safe_name = name.rsplit(".", 1)[0].replace(" ", "_") + ".jpg"
                            dest_path = f"{case_folder}/{safe_name}"
                            if upload_new_file(dbx, content, dest_path):
                                photo_links.append(dest_path)

                        row = {
                            "Serial_No": serial_no,
                            "GSTINs": "; ".join(valid_gstins),
                            "Trade_Names": "; ".join(trade_names_list),
                            "Case_Summary": case_summary.strip(),
                            "Category": category,
                            "Investigation_Group": investigation_group,
                            "Status": status,
                            "Date_of_Approval": date_of_approval.strftime("%Y-%m-%d"),
                            "Uploaded_By": st.session_state.username,
                            "Uploaded_On": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "Photo_Links": "; ".join(photo_links),
                        }

                        if append_case_row(dbx, CASES_DATA_PATH, row):
                            st.success(f"Case #{serial_no} saved successfully!")
                            _reset_upload_state()
                            st.rerun()
                        else:
                            st.error("Failed to save the case to the data sheet. Please try again.")
