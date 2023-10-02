import os
import pandas as pd
from pathlib import Path
from pydub import AudioSegment
from typing import Literal, Optional

from src.clients.database import Database
from src.clients.scp_transfer import FileTransfer
from src.clients.storage_base import BaseStorage

from src.utils.logger import logger
from src.config import CONFIG
from src.models.file import FileToUpload
from src.models.audio import Audio
from src.models.segment import Segment, SegmentCreate, SegmentCreateInDB


class OutputPersistanceService:
    def __init__(
        self,
        output_folder: Path,
        db: Optional[Database] = None,
        file_transfer_client: Optional[FileTransfer] = None,
        remote_storage_client: Optional[BaseStorage] = None,
    ):
        self.output_folder = output_folder
        self.output_folder.mkdir(parents=True, exist_ok=True)

        self.db = db
        self.file_transfer_client = file_transfer_client
        self.remote_storage_client = remote_storage_client

    def save_transcription(
        self,
        corpus_id: int,
        audio: Audio,
        segments: list[Segment],
        audio_export_format: Literal["wav", "mp3"] = "wav",
        remote_storage_folder_id: Optional[str] = None,
    ):
        saved_segments = []

        for segment in segments:
            try:
                saved_segment = self._save_transcription_to_file(
                    audio, segment, audio_export_format
                )

                if saved_segment is None:
                    logger.error(
                        f"Erro ao processar segmento {segment.segment_num} in {audio.name}",
                        stack_info=True,
                    )
                    continue

                if self.db is not None:
                    self._save_transcription_to_db(corpus_id, audio, saved_segment)

                if self.file_transfer_client is not None:
                    self.file_transfer_client.put(
                        source=saved_segment.segment_path,
                        target=os.path.join(
                            CONFIG.remote.dataset_path, saved_segment.segment_path
                        ),
                    )
                if (
                    self.remote_storage_client is not None
                    and remote_storage_folder_id is not None
                ):
                    self._save_transcription_to_remote(
                        remote_storage_folder_id, audio, saved_segment
                    )

                saved_segments.append(saved_segment.dict())

            except Exception as e:
                logger.error(
                    f"Erro ao processar segmento {segment.segment_num} in {audio.name}: {e}",
                    stack_info=True,
                )
                return None

        df = pd.DataFrame(saved_segments)
        df.to_csv(
            self.output_folder / "summary.csv",
            index=False,
            encoding="utf-8",
            sep="|",
            mode="w",
        )

    def _save_transcription_to_file(
        self, audio: Audio, segment: Segment, audio_export_format: str
    ) -> Optional[SegmentCreate]:
        if self.output_folder is None:
            raise Exception(
                "Output folder not provided. Cannot save transcription to file."
            )

        output_audio_folder = Path(self.output_folder / "audios")
        output_transcription_folder = Path(self.output_folder / "transcriptions")

        for folder in (output_audio_folder, output_transcription_folder):
            folder.mkdir(parents=True, exist_ok=True)

        try:
            original_start_time = audio.start_offset_trimmed_audio + segment.start_time
            original_end_time = audio.start_offset_trimmed_audio + segment.end_time
            speaker_id = int(segment.speaker) if segment.speaker is not None else -1
            segment_name = f"{segment.segment_num:04}_{audio.name}_{original_start_time}_{original_end_time}"

            transc_path = os.path.join(
                output_transcription_folder, f"{segment_name}.txt"
            )
            transcription = segment.text_asr
            with open(transc_path, "w", encoding="utf-8") as f:
                f.write(transcription)

            segment_path_on_local = os.path.join(
                output_audio_folder, f"{segment_name}.{audio_export_format}"
            )

            audio_segment = AudioSegment(
                audio.trimmed_audio[
                    int(segment.start_time * 1000) : int(segment.end_time * 1000)
                ]
            )
            audio_segment.export(segment_path_on_local, format=audio_export_format)

            return SegmentCreate(
                **segment.dict(),
                original_start_time=original_start_time,
                original_end_time=original_end_time,
                speaker_id=speaker_id,
                segment_name=segment_name,
                segment_path=segment_path_on_local,
                extension=audio_export_format,
            )
        except Exception as e:
            logger.error(
                f"Erro ao processar segmento {segment.segment_num} in {audio.name}: {e}",
                stack_info=True,
            )
            return None

    def _save_transcription_to_db(
        self, corpus_id: int, audio: Audio, segment: SegmentCreate
    ):
        if self.db is None:
            raise Exception(
                "Database client not provided. Cannot save transcription to database."
            )

        logger.info(f"Creating audio {audio.name} on database")
        audio_id = self.db.add_audio(audio.name, corpus_id, audio.duration)
        segment_to_db = SegmentCreateInDB(**segment.dict(), audio_id=audio_id)
        self.db.add_audio_segment(segment_to_db)

    def _save_transcription_to_remote(
        self,
        folder_parent_id: str,
        audio: Audio,
        segment: SegmentCreate,
    ):
        if self.remote_storage_client is None:
            raise Exception(
                "Remote storage client not provided. Cannot save transcription to remote storage."
            )

        file_to_upload = FileToUpload(
            name=segment.segment_name,
            path=segment.segment_path,
            extension=segment.extension,
        )

        self.remote_storage_client.upload_file_to_folder(
            folder_parent_id, file_to_upload
        )
