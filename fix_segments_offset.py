import sys
import os

sys.path.append(os.path.abspath(os.path.join("..")))

from logging import DEBUG
import locale
import os
from tqdm import tqdm
from typing import Literal, Callable

from src.steps.audio_loader import AudioLoaderGoogleDrive
from src.utils import google_drive, logger as lg
from src.utils.database import Database
from src.config import CONFIG
from src.models.audio import Audio

locale.getpreferredencoding = lambda: "UTF-8"


logger = lg.logger
logger.setLevel(level=DEBUG)


def analyze_differences_in_durations(
    folders_to_explore,
    format: Literal[".wav", ".mp4"],
    get_db_search_key: Callable[..., str] = lambda x: x,
):
    with Database() as db:
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
                audio_in_db = (
                    audios_with_name.iloc[0] if not audios_with_name.empty else None
                )
                if audio_in_db is None:
                    logger.info(f"Audio {audio_name} not in database. Skipping...")
                    continue

                audio_drive_id = item["id"]

                logger.debug(f"Loading audio {audio_name} from Google Drive")
                audio_ndarray, non_silent_indexes = AudioLoaderGoogleDrive(
                    google_drive_service,
                    sample_rate=CONFIG.sample_rate,
                    mono_channel=CONFIG.mono_channel,
                ).load_and_downsample(audio_drive_id, format)

                audio = Audio(
                    name=audio_name,
                    bytes=audio_ndarray,
                    sample_rate=CONFIG.sample_rate,
                    non_silent_interval=non_silent_indexes,
                )

                import json

                audio_dict = {
                    "name": audio.name,
                    "sample_rate": audio.sample_rate,
                    "non_silent_interval": list(audio.non_silent_interval),
                    "duration": audio.duration,
                    "start_offset_trimmed_audio": audio.start_offset_trimmed_audio,
                    "end_offset_trimmed_audio": audio.end_offset_trimmed_audio,
                }

                logger.info(f"Audio: {audio_dict}")
                if audio.duration != audio_in_db["duration"]:
                    logger.info(
                        f"Audio {audio_name} has different durations: {audio.duration} vs {audio_in_db['duration']}."
                    )


if __name__ == "__main__":
    CORPUS_ID = 2

    folders_to_explore = {
        "nurc_sp/EF": {
            "folder_id": "1ndi8t_7shb3FB77ZTWd7xVW9KgLm6NLA",
        },
        "nurc_sp/DID": {
            "folder_id": "1npveVhN9h5fsWhJzVKDUD7uQv76MNZ4i",
        },
        "nurc_sp/D2": {
            "folder_id": "1njSedHukKrN8zJGM12eL-rt3aaOZpxdO",
        },
    }
    format = ".wav"

    analyze_differences_in_durations(folders_to_explore, format)