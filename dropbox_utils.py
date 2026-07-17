# dropbox_utils.py
import time
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st
import dropbox
from dropbox.exceptions import AuthError, ApiError

from config import (
    DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN,
    LOG_FILE_PATH, DATA_SHEET_COLUMNS
)


def get_dropbox_client():
    """Initializes and returns the Dropbox client using a refresh token."""
    try:
        if not all([DROPBOX_APP_KEY, DROPBOX_APP_SECRET, DROPBOX_REFRESH_TOKEN]):
            st.error("Dropbox credentials are not found in Streamlit secrets.")
            return None

        dbx = dropbox.Dropbox(
            app_key=DROPBOX_APP_KEY,
            app_secret=DROPBOX_APP_SECRET,
            oauth2_refresh_token=DROPBOX_REFRESH_TOKEN
        )
        dbx.users_get_current_account()
        return dbx

    except AuthError as e:
        st.error(f"Authentication Error: Please check your Dropbox credentials. Details: {e}")
        return None
    except Exception as e:
        st.error(f"Failed to connect to Dropbox: {e}")
        return None


def create_folder(dbx, folder_path):
    """Creates a folder in Dropbox if it doesn't already exist."""
    try:
        dbx.files_create_folder_v2(folder_path)
    except ApiError as e:
        if e.error.is_path() and e.error.get_path().is_conflict():
            pass  # Folder already exists
        else:
            st.error(f"Dropbox API error during folder creation: {e}")


def upload_file(dbx, file_content, dropbox_path):
    """Uploads/overwrites a file at dropbox_path, keeping the same filename."""
    try:
        dbx.files_upload(
            file_content,
            dropbox_path,
            mode=dropbox.files.WriteMode.update(rev="latest")
        )
        return True
    except Exception:
        pass  # fall through to temp-then-move

    temp_path = dropbox_path.rsplit('.', 1)[0] + f"_temp_{int(time.time())}." + dropbox_path.rsplit('.', 1)[-1]
    try:
        dbx.files_upload(file_content, temp_path)
        try:
            dbx.files_delete_v2(dropbox_path)
        except Exception:
            pass
        dbx.files_move_v2(temp_path, dropbox_path)
        return True
    except Exception as e:
        st.error(f"❌ Upload failed for {dropbox_path}: {e}")
        try:
            dbx.files_delete_v2(temp_path)
        except Exception:
            pass
        return False


def upload_new_file(dbx, file_content, dropbox_path):
    """Uploads a brand-new file (e.g. a case photo) - simple add, no overwrite logic needed."""
    try:
        dbx.files_upload(file_content, dropbox_path, mode=dropbox.files.WriteMode('add'))
        return True
    except ApiError as e:
        st.error(f"Dropbox API error during photo upload: {e}")
        return False


def download_file(dbx, dropbox_path):
    """Downloads a file from Dropbox. Returns None if it doesn't exist."""
    try:
        _, res = dbx.files_download(path=dropbox_path)
        return res.content
    except ApiError as e:
        if isinstance(e.error, dropbox.files.DownloadError) and e.error.is_path() and e.error.get_path().is_not_found():
            return None
        st.error(f"Dropbox API error during download: {e}")
        return None


def get_shareable_link(dbx, dropbox_path):
    """Gets (or creates) a shareable link for a file."""
    try:
        links = dbx.sharing_list_shared_links(path=dropbox_path, direct_only=True).links
        if links:
            return links[0].url
        settings = dropbox.sharing.SharedLinkSettings(
            requested_visibility=dropbox.sharing.RequestedVisibility.public
        )
        link = dbx.sharing_create_shared_link_with_settings(dropbox_path, settings=settings)
        return link.url
    except ApiError:
        try:
            links = dbx.sharing_list_shared_links(path=dropbox_path).links
            if links:
                return links[0].url
        except ApiError:
            pass
        return None


def read_from_spreadsheet(dbx, dropbox_path):
    """Reads an Excel file in Dropbox into a pandas DataFrame."""
    file_content = download_file(dbx, dropbox_path)
    if file_content:
        try:
            return pd.read_excel(BytesIO(file_content))
        except Exception as e:
            st.error(f"Error reading Excel file from Dropbox: {e}")
            return pd.DataFrame()
    return pd.DataFrame()


def update_spreadsheet_from_df(dbx, df_to_write, dropbox_path):
    """Writes a DataFrame to Excel in memory and uploads it to Dropbox."""
    try:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_to_write.to_excel(writer, index=False, sheet_name='Sheet1')
        processed_data = output.getvalue()
        return upload_file(dbx, processed_data, dropbox_path)
    except Exception as e:
        st.error(f"Error writing Excel file for Dropbox upload: {e}")
        return False


def get_next_serial_no(dbx, dropbox_path):
    """Reads the data sheet and returns the next running serial number."""
    df = read_from_spreadsheet(dbx, dropbox_path)
    if df.empty or "Serial_No" not in df.columns:
        return 1
    try:
        return int(pd.to_numeric(df["Serial_No"], errors="coerce").max()) + 1
    except (ValueError, TypeError):
        return len(df) + 1


def append_case_row(dbx, dropbox_path, row_dict):
    """Appends a single case record (dict) to the central data sheet."""
    df = read_from_spreadsheet(dbx, dropbox_path)
    if df.empty:
        df = pd.DataFrame(columns=DATA_SHEET_COLUMNS)
    new_row = pd.DataFrame([row_dict])
    df = pd.concat([df, new_row], ignore_index=True)
    return update_spreadsheet_from_df(dbx, df, dropbox_path)


def update_case_row(dbx, dropbox_path, serial_no, updated_fields: dict):
    """Updates an existing row identified by Serial_No with the given fields."""
    df = read_from_spreadsheet(dbx, dropbox_path)
    if df.empty or "Serial_No" not in df.columns:
        return False
    mask = pd.to_numeric(df["Serial_No"], errors="coerce") == int(serial_no)
    if not mask.any():
        return False
    for k, v in updated_fields.items():
        df.loc[mask, k] = v
    return update_spreadsheet_from_df(dbx, df, dropbox_path)


def log_activity(dbx, username, role):
    """Appends a login activity record to the log file in Dropbox."""
    if not dbx:
        return False
    log_columns = ['Timestamp', 'Username', 'Role']
    df_logs = read_from_spreadsheet(dbx, LOG_FILE_PATH)
    if df_logs.empty or list(df_logs.columns) != log_columns:
        df_logs = pd.DataFrame(columns=log_columns)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_log_entry = pd.DataFrame([{'Timestamp': timestamp, 'Username': username, 'Role': role}])
    df_logs = pd.concat([df_logs, new_log_entry], ignore_index=True)
    return update_spreadsheet_from_df(dbx, df_logs, LOG_FILE_PATH)


def list_files(dbx, folder_path):
    """Lists all file names in a specific folder in Dropbox."""
    try:
        res = dbx.files_list_folder(folder_path)
        return [entry.name for entry in res.entries]
    except ApiError as e:
        st.error(f"Dropbox API error while listing files: {e}")
        return []
