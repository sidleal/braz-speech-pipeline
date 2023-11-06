import locale
from logging import DEBUG
from pathlib import Path
from tqdm import tqdm
import locale
from pandas import DataFrame
import pandas as pd
from typing import List, Optional

from src.services.exporter import Exporter

from src.clients.database import Database
from src.models.file import AudioFormat

from src.utils import logger as lg

locale.getpreferredencoding = lambda: "UTF-8"


logger = lg.get_logger(__name__)
logger.setLevel(level=DEBUG)


def export_corpus_dataset(
    corpus_id: int,
    output_folder: Path,
    db: Database,
    debug: bool = False,
    export_audio_to_formats: List[AudioFormat] = [AudioFormat.WAV, AudioFormat.MP3],
    sample_rate: int = 48000,
    google_drive_folder_ids: Optional[List[str]] = None,
    filter_format: Optional[AudioFormat] = None,
    export_original_audios: bool = False,
    export_to_csv: bool = False,
    export_concanated_text: bool = False,
    export_speakers_text: bool = False,
    export_text_grid: bool = False,
):
    audios = db.get_audios_by_corpus_id(corpus_id, filter_finished=True)

    if not isinstance(audios, DataFrame) or audios.empty:
        logger.info(f"No audios found for corpus {corpus_id}.")
        return

    if debug:
        audios = audios.sample(10)

    segments = db.get_segments_by_audios_id_list(audios.id.tolist())

    if not isinstance(segments, DataFrame) or segments.empty:
        logger.info(f"No segments found for corpus {corpus_id}.")
        return

    exporter = Exporter(output_folder)

    if export_original_audios:
        assert (
            google_drive_folder_ids is not None
        ), "You must provide at least one folder ID from Google Drive for exporting original audios."
        assert (
            filter_format is not None
        ), "You must provide a format for searching the audio files in Google Drive (wav or mp3)."
        logger.info(
            f"Exporting original audios for corpus {corpus_id}. This may take a while."
        )
        exporter.export_original_audios(
            audios,
            google_drive_folder_ids,
            filter_format,
            sample_rate,
            export_audio_to_formats,
        )

    if export_to_csv:
        logger.info(f"Exporting audios and segments for corpus {corpus_id} to csv.")
        exporter.export_to_csv(corpus_id, audios, segments)

    if export_concanated_text or export_speakers_text or export_text_grid:
        audios = audios.rename(
            columns={
                "id": "audio_id",
                "name": "audio_name",
                "duration": "audio_duration",
            }
        )
        # Joining the DataFrames
        merged_df = pd.merge(segments, audios, on="audio_id")

        # Group by audio_id
        grouped = merged_df.groupby("audio_id")

        for audio_id, group in tqdm(grouped):
            # Get the audio_name for this audio_id
            audio_name = group["audio_name"].iloc[0]

            logger.info(
                f"Working on the export of audio {audio_name} for corpus {corpus_id}."
            )

            # Sort the group by segment_num
            sorted_group = group.sort_values("segment_num")

            if export_concanated_text:
                logger.info(
                    f"Exporting concatenated text files for corpus {corpus_id}."
                )
                exporter.export_concatenated_text_files(audio_name, sorted_group)

            if export_speakers_text:
                logger.info(f"Exporting speakers text files for corpus {corpus_id}.")
                exporter.export_speakers_text_file(audio_name, sorted_group)

            if export_text_grid:
                logger.info(f"Exporting text grid files for corpus {corpus_id}.")
                exporter.export_textgrid_file(audio_name, sorted_group)

    # logger.info(f"Found {len(audios)} audios for corpus {corpus_id}.")
    # files: List[File] = storage_client.get_files_from_folder(
    #     folder_id=folder_id, filter_format=format_filter
    # )
    # logger.info(
    #     f"On the folder {folder_id}, we have {len(files)} audios{f' with format {format_filter.value}' if format_filter else ''}."
    # )
