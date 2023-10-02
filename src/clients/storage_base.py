from abc import ABC, abstractmethod
from io import BytesIO
from typing import Optional, Literal

from src.models.file import File, FileToUpload


class BaseStorage(ABC):
    @abstractmethod
    def get_files_from_folder(
        self, folder_id, filter_format: Optional[str] = None
    ) -> list[File]:
        pass

    @abstractmethod
    def get_file_content(self, file_name) -> BytesIO:
        pass

    @abstractmethod
    def upload_file_to_folder(
        self, parent_folder_id, file: FileToUpload
    ) -> Optional[str]:
        pass

    @abstractmethod
    def upload_folder_to_folder(self, parent_folder_id, folder_path) -> list[str]:
        pass

    @abstractmethod
    def create_folder(self, folder_name, parent_folder_id) -> Optional[str]:
        pass

    @abstractmethod
    def get_folder_by_name(self, parent_id, folder_name) -> Optional[str]:
        pass
