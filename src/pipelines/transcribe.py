import locale
from logging import DEBUG
from pathlib import Path
from tqdm import tqdm
import locale
from tqdm import tqdm
from typing import Literal, Callable, Optional
from pandas import DataFrame

from src.services.audio_loader_service import AudioLoaderService
from src.services.transcription_service import TranscriptionService
from src.services.output_persistance_service import OutputPersistanceService

from src.clients.google_drive import GoogleDriveClient
from src.clients.database import Database
from src.clients.scp_transfer import FileTransfer

from src.models.audio import Audio
from src.models.segment import Segment
from src.models.file import File

from src.utils import logger as lg
from src.utils.exceptions import EmptyAudio

from src.config import CONFIG

locale.getpreferredencoding = lambda: "UTF-8"


logger = lg.logger
logger.setLevel(level=DEBUG)


def transcribe_audios_in_folder(
    corpus_id: int,
    folder_id: str,
    output_folder: Path,
    db: Optional[Database] = None,
    file_transfer_client: Optional[FileTransfer] = None,
    save_to_drive: bool = False,
    storage_output_folder_id: Optional[str] = None,
    format_filter: Optional[Literal["wav", "mp4", "mp3"]] = "wav",
    get_db_search_key: Callable[..., str] = lambda x: x,
):
    storage_client = GoogleDriveClient()

    files: list[File] = storage_client.get_files_from_folder(
        folder_id=folder_id, filter_format=format_filter
    )
    logger.info(
        f"On the folder {folder_id}, we have {len(files)} audios{f' with format {format_filter}' if format_filter else ''}."
    )
    for audio in tqdm(files):
        # Handle NURC special conditions
        audio.name = (
            audio.name.replace("_sem_cabecalho", "")
            .replace("_sem_cabecallho", "")
            .replace("_sem_cabeçalho", "")
        )
        if db is not None:
            audios_with_name = db.get_audios_by_name(get_db_search_key(audio.name))
            if isinstance(audios_with_name, DataFrame) and not audios_with_name.empty:
                logger.info(f"Audio {audio.name} already processed. Skipping...")
                continue

        logger.info(f"Processing audio {audio.name}.")
        audio_loader_service = AudioLoaderService(storage_client)
        try:
            audio_to_process: Audio = audio_loader_service.load_audio(
                audio, CONFIG.sample_rate, CONFIG.mono_channel
            )

            segments: list[Segment] = TranscriptionService(
                CONFIG.computation.whisper_model,
                CONFIG.computation.batch_size,
                CONFIG.computation.compute_type,
            ).transcribe(audio_to_process)

            OutputPersistanceService(
                output_folder,
                db=db,
                file_transfer_client=file_transfer_client,
                remote_storage_client=storage_client if save_to_drive else None,
            ).save_transcription(
                corpus_id=corpus_id,
                audio=audio_to_process,
                segments=segments,
                audio_export_format="wav",
                remote_storage_folder_id=storage_output_folder_id or folder_id,
            )

        except EmptyAudio as e:
            logger.error(f"Audio {audio.name} with error and couldn't be loaded.")
            continue

    pass
