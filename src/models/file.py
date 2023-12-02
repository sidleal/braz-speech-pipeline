from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

from src.utils.files import get_mime_from_extension


class AudioFormat(str, Enum):
    WAV = "wav"
    MP4 = "mp4"
    MP3 = "mp3"


class File(BaseModel):
    id: str
    name: str
    mime_type: str
    extension: AudioFormat
    parents: List[str]
    size: int

    @property
    def _extension(self) -> str:
        return "." + self.extension.replace(".", "")

    @staticmethod
    def clean_name(name: str) -> str:
        return (
            name.replace("_sem_cabecalho", "")
            .replace("_sem_cabecallho", "")
            .replace("_sem_cabeçalho", "")
            .strip()
            .split("/")[-1]
            .split(".")[0]
        )


class FileToUpload(BaseModel):
    name: str
    extension: Optional[str] = None
    path: Optional[str] = None
    content: Optional[bytes] = None
    mime_type: Optional[str] = None

    @property
    def mime_from_extension(self):
        return get_mime_from_extension(self.extension) if self.extension else None
