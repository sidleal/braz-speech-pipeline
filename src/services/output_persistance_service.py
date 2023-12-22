import os
import pandas as pd
from pathlib import Path
from pydub import AudioSegment
from typing import Literal, Optional
import soundfile as sf

from src.clients.database import Database
from src.clients.scp_transfer import FileTransfer
from src.clients.storage_base import BaseStorage
from src.clients.google_drive import GoogleDriveClient

from src.utils.logger import get_logger
from src.config import CONFIG
from src.models.file import FileToUpload, AudioFormat
from src.models.audio import Audio
from src.models.segment import Segment, SegmentCreate, SegmentCreateInDB

logger = get_logger(__name__)
logger.setLevel("DEBUG")

class OutputPersistanceService:
    def __init__(
        self,
        output_folder: Path,
        db: Optional[Database] = None,
        file_transfer_client: Optional[FileTransfer] = None,
        remote_storage_client: Optional[GoogleDriveClient] = None,
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
        audio_export_format: AudioFormat = AudioFormat.WAV,
        remote_storage_folder_id: Optional[str] = None,
    ):
        saved_segments = []
        logger.info(f"Persisting data for audio {audio.name} transcription")

        if self.db is not None:
            logger.info(f"Creating audio {audio.name} on database")
            audio_id_in_db = self.db.add_audio(audio.name, corpus_id, audio.duration)

        try:
            # Save all segments locally
            for segment in segments:
                logger.debug("Saving to files")
                saved_segment = self._save_transcription_to_file(
                    audio, segment, audio_export_format.value
                )

                if saved_segment is None:
                    logger.error(
                        f"Erro ao processar segmento {segment.segment_num} in {audio.name}",
                        stack_info=True,
                    )
                else:
                    saved_segments.append(saved_segment)

            # Transfer files to server
            if self.file_transfer_client is not None:
                logger.debug("Transfering to server")
                self.file_transfer_client.put(
                    source=[saved_segment.segment_path for saved_segment in saved_segments],
                    target=os.path.join(
                        CONFIG.remote.dataset_path, os.path.dirname(saved_segment.segment_path),
                    ),
                    target_is_folder=True,
                )

            # Save to database
            if self.db is not None:
                for saved_segment in saved_segments:
                    logger.debug("Saving to DB")
                    self._save_transcription_to_db(corpus_id, audio, saved_segment, audio_id_in_db)
                
            # Save to remote storage
            if self.remote_storage_client is not None:
                for saved_segment in saved_segments:
                    logger.debug("Saving to Google Drive")
                    self._save_transcription_to_remote(
                        remote_storage_folder_id, audio, saved_segment
                    )

        except Exception as e:
            logger.error(
                f"Erro ao processar {audio.name}: {e}",
                stack_info=True,
            )
            return

        df = pd.DataFrame(saved_segments)
        df.to_csv(
            self.output_folder / audio.name / "summary.csv",
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

        output_audio_folder = Path(self.output_folder / audio.name / "audios")
        output_transcription_folder = Path(self.output_folder / audio.name / "texts")

        for folder in (output_audio_folder, output_transcription_folder):
            folder.mkdir(parents=True, exist_ok=True)

        try:
            original_start_time = audio.start_offset_trimmed_audio + segment.start_time
            original_end_time = audio.start_offset_trimmed_audio + segment.end_time
            speaker_id = int(segment.speaker) if segment.speaker is not None else -1
            segment_name = f"{segment.segment_num:04}_{os.path.basename(audio.name)}_{original_start_time:.2f}_{original_end_time:.2f}"

            transc_path = os.path.join(
                output_transcription_folder, f"{segment_name}.txt"
            )
            transcription = segment.text_asr
            with open(transc_path, "w", encoding="utf-8") as f:
                f.write(transcription)

            segment_path_on_local = os.path.join(
                output_audio_folder, f"{segment_name}.{audio_export_format}"
            )

            sf.write(segment_path_on_local,audio.trimmed_audio[
                    int(segment.start_time * audio.sample_rate) : int(segment.end_time * audio.sample_rate)
                ], audio.sample_rate )

            segment_saved = SegmentCreate(
                **segment.dict(),
                speaker_id=speaker_id,
                segment_name=segment_name,
                segment_path=segment_path_on_local,
                extension=audio_export_format,
            )
            segment_saved.start_time = original_start_time
            segment_saved.end_time = original_end_time
            
            logger.info(segment_saved)
            return segment_saved
        except Exception as e:
            logger.error(
                f"Erro ao processar segmento {segment.segment_num} in {audio.name}: {e}",
                stack_info=True,
            )
            return None

    def _save_transcription_to_db(
        self, corpus_id: int, audio: Audio, segment: SegmentCreate, audio_id_in_db: int
    ):
        if self.db is None:
            raise Exception(
                "Database client not provided. Cannot save transcription to database."
            )

        segment_to_db = SegmentCreateInDB(**segment.dict(), audio_id=audio_id_in_db)
        self.db.add_audio_segment(segment_to_db)

    def _save_transcription_to_remote(
        self,
        folder_parent_id: Optional[str],
        audio: Audio,
        segment: SegmentCreate,
    ):
        if self.remote_storage_client is None:
            raise Exception(
                "Remote storage client not provided. Cannot save transcription to remote storage."
            )

        for ext, folder in (("wav", "audios"), ("txt", "texts")):
            file_to_upload = FileToUpload(
                name=os.path.join("transcriptions",audio.name, folder, segment.segment_name),
                path=(self.output_folder / audio.name / folder / f"{segment.segment_name}.{ext}").as_posix(),
                extension=ext,
            )

            if folder_parent_id is None:
                folder_parent_id = audio.parent_folder_id

            self.remote_storage_client.upload_file_to_folder(
                folder_parent_id, file_to_upload
            )
