import locale
from logging import DEBUG
from pathlib import Path
from tqdm import tqdm
import locale
from typing import Literal, Callable, Optional, List
from pandas import DataFrame

from src.services.audio_loader_service import AudioLoaderService
from src.services.transcription_service import TranscriptionService
from src.services.output_persistance_service import OutputPersistanceService

from src.clients.google_drive import GoogleDriveClient
from src.clients.database import Database
from src.clients.scp_transfer import FileTransfer

from src.models.audio import Audio
from src.models.segment import Segment
from src.models.file import File, AudioFormat

from src.utils import logger as lg
from src.utils.exceptions import EmptyAudio

from src.config import CONFIG

locale.getpreferredencoding = lambda: "UTF-8"


logger = lg.get_logger(__name__)
logger.setLevel(level=DEBUG)


def export_corpus_dataset(
    corpus_id: int,
    folder_id: str,
    output_folder: Path,
    db: Database,
    format_filter: Optional[AudioFormat] = None,
    get_db_search_key: Callable[..., str] = lambda x: x,
):
    storage_client = GoogleDriveClient()
    audio_loader_service = AudioLoaderService(storage_client)

    files: List[File] = storage_client.get_files_from_folder(
        folder_id=folder_id, filter_format=format_filter
    )
    logger.info(
        f"On the folder {folder_id}, we have {len(files)} audios{f' with format {format_filter.value}' if format_filter else ''}."
    )
    for audio in tqdm(files[:1]):
        # Handle NURC special conditions
        audio.name = (
            audio.name.replace("_sem_cabecalho", "")
            .replace("_sem_cabecallho", "")
            .replace("_sem_cabeçalho", "")
        )

        audios_with_name = db.get_audios_by_name(get_db_search_key(audio.name))
        print(audios_with_name)
        if isinstance(audios_with_name, DataFrame) and not audios_with_name.empty:
            logger.info(f"Audio {audio.name} already processed. Skipping...")
            continue

        try:
            logger.info(f"Loading audio {audio.name}.")
            audio_to_process: Audio = audio_loader_service.load_audio(
                audio, CONFIG.sample_rate, CONFIG.mono_channel
            )
            logger.info(audio_to_process)
            logger.info(f"Audio loaded.")

        except EmptyAudio as e:
            logger.error(f"Audio {audio.name} with error and couldn't be loaded.")
            continue

        except Exception as e:
            logger.error(f"Something went wrong when processing audio {audio.name}")
            continue

    pass
