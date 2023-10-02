from pathlib import Path
from logging import DEBUG
import torch
from tqdm import tqdm
import locale
import os
import whisperx
from tqdm import tqdm
from typing import Literal, Callable

from src.steps import AudioLoaderGoogleDrive, AudioToTextSegmentsConverter
from src.utils import google_drive, logger as lg
from src.clients.database import Database
from src.config import CONFIG
from src.models.audio import Audio
from src.utils.exceptions import EmptyAudio


locale.getpreferredencoding = lambda: "UTF-8"


logger = lg.logger
logger.setLevel(level=DEBUG)

# Load whisper model
device = "cuda" if torch.cuda.is_available() else "cpu"
batch_size = 8
compute_type = "float16"
WHISPER_MODEL = "large-v2"


def diarize_and_transcribe(
    data_path: Path,
    corpus_id,
    folders_to_explore,
    format: Literal[".wav", ".mp4"],
    get_db_search_key: Callable[..., str] = lambda x: x,
):
    with Database() as db:
        logger.info(f"Loading whisper model {WHISPER_MODEL}")
        whisperx_model = whisperx.load_model(
            WHISPER_MODEL, device, compute_type=compute_type, language="pt"
        )

        logger.info(f"Stablishing Google Drive connection")
        google_drive_service = google_drive.setup_service()

        for folder_name, folder in folders_to_explore.items():
            logger.info(f"Exploring folder {folder_name}")

            files_in_folder = google_drive.get_files_from_folder(
                folder["folder_id"], format
            )
            logger.info(
                f"On the folder {folder_name}, we have {len(files_in_folder)} audios."
            )

            for item in tqdm(files_in_folder):
                audio_name = os.path.splitext(item["name"])[0]

                # Handle NURC special conditions
                audio_name = (
                    audio_name.replace("_sem_cabecalho", "")
                    .replace("_sem_cabecallho", "")
                    .replace("_sem_cabeçalho", "")
                )

                audios_with_name = db.get_audios_by_name(get_db_search_key(audio_name))
                if not audios_with_name.empty:  # type: ignore
                    continue

                logger.info(f"Processing audio {audio_name}.")

                audio_drive_id = item["id"]

                logger.debug("Loading file from Google Drive")
                try:
                    audio_ndarray, non_silent_indexes = AudioLoaderGoogleDrive(
                        google_drive_service,
                        sample_rate=CONFIG.sample_rate,
                        mono_channel=CONFIG.mono_channel,
                    ).load_and_downsample(audio_drive_id, format)
                except EmptyAudio as e:
                    logger.error(
                        f"Audio {audio_name} with error and couldn't be loaded."
                    )
                    continue

                audio = Audio(
                    name=audio_name,
                    bytes=audio_ndarray,
                    sample_rate=CONFIG.sample_rate,
                    non_silent_interval=non_silent_indexes,
                )

                OUTPUT_PATH = data_path / folder_name / audio.name_with_no_spaces

                converter = AudioToTextSegmentsConverter(
                    output_path=OUTPUT_PATH, whisperx_model=whisperx_model
                )

                converter.diarize_and_transcribe(audio, corpus_id)
