from pydantic import BaseModel
from typing import Optional


class File(BaseModel):
    id: str
    name: str
    mime_type: str
    extension: str
    parents: list[str]
    size: int

    @property
    def _extension(self) -> str:
        return "." + self.extension.replace(".", "")


class FileToUpload(BaseModel):
    name: str
    extension: str
    path: Optional[str] = None
    content: Optional[bytes] = None
    mime_type: Optional[str] = None

    @property
    def mime_from_extension(self):
        return {
            "wav": "audio/wav",
            "mp3": "audio/mp3",
            "mp4": "video/mp4",
            "txt": "text/plain",
            ".doc": "application/vnd.google-apps.document",
            ".xls": "application/vnd.google-apps.spreadsheet",
            ".ppt": "application/vnd.google-apps.presentation",
            ".pdf": "application/pdf",
            ".jpg": "image/jpeg",
            ".png": "image/png",
            ".txt": "text/plain",
        }[self.extension]
