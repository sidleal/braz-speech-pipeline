import os
from googleapiclient.discovery import build
from google.oauth2 import service_account
from typing import Literal


def get_credentials():
    credentials = None
    scopes = ["https://www.googleapis.com/auth/drive.readonly"]
    keyfile_path = "./token.json"  # Replace with the path to your own keyfile

    try:
        credentials = service_account.Credentials.from_service_account_file(
            keyfile_path, scopes=scopes
        )
    except Exception as e:
        print("Error loading credentials:", e)

    return credentials


def setup_service():
    return build("drive", "v3", credentials=get_credentials())


def get_files_from_folder(folder_id, format: Literal[".wav", ".mp4"] = ".wav"):
    service = setup_service()
    query = f"'{folder_id}' in parents and trashed = false"
    return_files = []

    page_token = None
    while True:
        results = (
            service.files()
            .list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType, size, parents)",
                pageToken=page_token,
            )
            .execute()
        )
        items = results.get("files", [])

        for item in items:
            if item["mimeType"] == "application/vnd.google-apps.folder":
                return_files.extend(get_files_from_folder(item["id"], format))
            else:
                file_name = item["name"]
                file_extension = os.path.splitext(file_name)[1]
                if file_extension == format:
                    return_files.append(item)

        page_token = results.get("nextPageToken")
        if not page_token:
            break

    return return_files
