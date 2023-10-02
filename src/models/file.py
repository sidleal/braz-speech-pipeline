from pydantic import BaseModel
from typing import Optional

from src.utils.files import get_mime_from_extension


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
        return get_mime_from_extension(self.extension)
