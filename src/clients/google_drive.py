import os
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload
from google.oauth2 import service_account
from typing import Literal, Optional

from src.utils.logger import logger
from src.clients.storage_base import BaseStorage
from src.models.file import File, FileToUpload


class GoogleDriveClient(BaseStorage):
    def __init__(self) -> None:
        self.service = self.__setup_service()

    def __setup_service(self):
        return build("drive", "v3", credentials=self.__get_credentials())

    def __get_credentials(self, keyfile_path: str = "./token.json"):
        credentials = None
        scopes = ["https://www.googleapis.com/auth/drive"]
        keyfile_path = keyfile_path

        try:
            credentials = service_account.Credentials.from_service_account_file(
                keyfile_path, scopes=scopes
            )
        except Exception as e:
            print("Error loading credentials:", e)

        return credentials

    def get_files_from_folder(
        self, folder_id, filter_format: Optional[Literal["wav", "mp4", "mp3"]] = None
    ) -> list[File]:
        query = f"'{folder_id}' in parents and trashed = false"
        return_files = []

        page_token = None
        while True:
            results = (
                self.service.files()
                .list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType, size, fileExtension, parents)",
                    pageToken=page_token,
                )
                .execute()
            )
            items = results.get("files", [])

            for item in items:
                if item["mimeType"] == "application/vnd.google-apps.folder":
                    return_files.extend(
                        self.get_files_from_folder(item["id"], filter_format)
                    )
                else:
                    file_name, file_extension = os.path.splitext(item["name"])
                    if (
                        filter_format is None
                        or file_extension == filter_format
                        or item["fileExtension"] == filter_format
                    ):
                        file = File(
                            id=item["id"],
                            name=file_name,
                            size=int(item["size"]),
                            mime_type=item["mimeType"],
                            extension=item["fileExtension"],
                            parents=item["parents"],
                        )
                        return_files.append(file)

            page_token = results.get("nextPageToken")
            if not page_token:
                break

        return return_files

    def get_file_content(self, file: File) -> io.BytesIO:
        request = self.service.files().get_media(fileId=file.id)
        file_content = io.BytesIO()

        downloader = MediaIoBaseDownload(file_content, request)

        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return io.BytesIO(file_content.getvalue())

    def upload_file_to_folder(
        self, parent_folder_id, file: FileToUpload
    ) -> Optional[str]:
        levels = file.name.split("/")
        if len(levels) > 1:
            for level in levels[:-1]:
                parent_folder_id = self.create_folder(level, parent_folder_id)

        file_metadata = {"name": levels[-1], "parents": [parent_folder_id]}
        file_mime_type = file.mime_type or file.mime_from_extension
        if file.path is not None:
            media = MediaFileUpload(file.path, mimetype=file_mime_type)
        elif file.content is not None:
            media = MediaIoBaseUpload(
                io.BytesIO(file.content),
                mimetype=file_mime_type,
            )
        else:
            raise Exception("No file content or path provided")

        uploaded_file = (
            self.service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        logger.info("File ID: %s" % uploaded_file.get("id"))
        return uploaded_file.get("id", None)

    def upload_folder_to_folder(self, folder_id, folder_path) -> list[str]:
        uploaded_files = []
        file_metadata = {
            "name": os.path.basename(folder_path),
            "parents": [folder_id],
            "mimeType": "application/vnd.google-apps.folder",
        }
        file = self.service.files().create(body=file_metadata, fields="id").execute()
        logger.info("Folder ID: %s" % file.get("id"))
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path):
                uploaded_file = self.upload_file_to_folder(file.get("id"), file_path)
                if uploaded_file is not None:
                    uploaded_files.append(uploaded_file)
            elif os.path.isdir(file_path):
                self.upload_folder_to_folder(file.get("id"), file_path)
        return uploaded_files

    def create_folder(self, folder_name, parent_folder_id) -> str:
        levels = folder_name.split("/")
        if len(levels) > 1:
            for level in levels[:-1]:
                parent_folder_id = self.create_folder(level, parent_folder_id)
            return parent_folder_id
        else:
            existing_folder = self.get_folder_by_name(parent_folder_id, folder_name)
            if existing_folder is not None:
                return existing_folder["id"]

            file_metadata = {
                "name": folder_name,
                "parents": [parent_folder_id],
                "mimeType": "application/vnd.google-apps.folder",
            }
            file = (
                self.service.files().create(body=file_metadata, fields="id").execute()
            )
            logger.info("Folder ID: %s" % file.get("id"))
            return file.get("id")

    def get_folder_by_name(self, parent_id, folder_name) -> Optional[dict]:
        query = f"mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and name='{folder_name}'"
        results = (
            self.service.files()
            .list(q=query, fields="files(id, name, parents)")
            .execute()
        )
        files = results.get("files", [])

        if not files:
            return None
        else:
            return files[0]
