import sys
import os

import sys

sys.path.append("/Users/64926/projects/tarsila/braz-speech-pipeline/")


from logging import DEBUG
import locale
import os
from tqdm import tqdm
from pandas import DataFrame
from typing import Literal, Callable

from src.services.audio_loader_service import AudioLoaderService
from src.clients.google_drive import GoogleDriveClient
from src.utils import logger as lg
from src.clients.database import Database
from src.config import CONFIG
from src.models.audio import Audio
from src.models.file import AudioFormat

locale.getpreferredencoding = lambda: "UTF-8"


logger = lg.get_logger(__name__)
logger.setLevel(level=DEBUG)


def analyze_differences_in_durations(
    folders_to_explore,
    format: AudioFormat,
    get_db_search_key: Callable[..., str] = lambda x: x,
):
    with Database() as db:
        logger.info(f"Stablishing Google Drive connection")
        google_drive_service = GoogleDriveClient()

        for folder_name, folder in folders_to_explore.items():
            logger.info(f"Exploring folder {folder_name}")

            files_in_folder = google_drive_service.get_files_from_folder(
                folder["folder_id"], format
            )
            logger.info(
                f"On the folder {folder_name}, we have {len(files_in_folder)} audios."
            )

            for item in tqdm(files_in_folder):
                audio_name = os.path.splitext(item.name)[0]

                # Handle NURC special conditions
                audio_name = (
                    audio_name.replace("_sem_cabecalho", "")
                    .replace("_sem_cabecallho", "")
                    .replace("_sem_cabeçalho", "")
                )

                audios_with_name = db.get_audios_by_name(
                    get_db_search_key(audio_name),
                    ignore_errors=True
                )
                if (
                    isinstance(audios_with_name, DataFrame)
                    and not audios_with_name.empty
                ):
                    audio_in_db = (
                        audios_with_name.iloc[0] if not audios_with_name.empty else None
                    )
                    if audio_in_db is None:
                        logger.info(f"Audio {audio_name} not in database. Skipping...")
                        continue
                else:
                    logger.info(f"Audio {audio_name} not in database. Skipping...")
                    continue

                logger.debug(f"Loading audio {audio_name} from Google Drive")
                audio = AudioLoaderService(
                    google_drive_service,
                ).load_audio(
                    item, CONFIG.sample_rate, CONFIG.mono_channel, normalize=True
                )

                audio_dict = {
                    "name": audio.name,
                    "sample_rate": audio.sample_rate,
                    "non_silent_interval": list(audio.non_silent_interval),
                    "duration": audio.duration,
                    "start_offset_trimmed_audio": audio.start_offset_trimmed_audio,
                    "end_offset_trimmed_audio": audio.end_offset_trimmed_audio,
                }

                logger.info(f"Audio: {audio_dict}")
                if abs(audio.duration - audio_in_db["duration"]) > 0.5:
                    logger.info(
                        f"Audio {audio_name} has different durations: {audio.duration} vs {audio_in_db['duration']}."
                    )
                    logger.info(
                        f"After fixing duration, it would be: {audio_in_db['duration'] + audio.start_offset_trimmed_audio + audio.end_offset_trimmed_audio} vs. {audio.duration}."
                    )
                    segments = db.get_segments_by_audio_id(audio_in_db["id"])

                    if isinstance(segments, DataFrame) and not segments.empty:
                        segments["start_time"] = (
                            segments["start_time"] + audio.start_offset_trimmed_audio
                        )
                        segments["end_time"] = (
                            segments["end_time"] + audio.start_offset_trimmed_audio
                        )

                        logger.info(
                            segments[["text_asr", "start_time", "end_time"]].head(5)
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
    format = AudioFormat.WAV

    analyze_differences_in_durations(folders_to_explore, format)
