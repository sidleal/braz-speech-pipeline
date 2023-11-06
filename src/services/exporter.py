from pathlib import Path
import pandas as pd
import textgrid
from typing import List
import soundfile as sf
import librosa

from src.models.file import AudioFormat
from src.clients.google_drive import GoogleDriveClient
from src.services.audio_loader_service import AudioLoaderService
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Exporter:
    def __init__(self, output_folder: Path):
        output_folder.mkdir(parents=True, exist_ok=True)
        self.output_folder = output_folder

    def export_to_csv(
        self, corpus_id: int, audios: pd.DataFrame, segments: pd.DataFrame
    ):
        audios.to_csv(
            self.output_folder / f"corpus_{corpus_id}_audios.csv", index=False
        )
        segments.to_csv(
            self.output_folder / f"corpus_{corpus_id}_segments.csv", index=False
        )
        segments.to_parquet(
            self.output_folder / f"corpus_{corpus_id}_segments.parquet", index=False
        )
        pass

    def export_concatenated_text_files(self, audio_name: str, group):
        # sorted_group = group.sort_values('segment_num')

        # Concatenate the text
        concatenated_text = " ".join(group["text"]).replace("\n", "")

        output_file_path = self.output_folder / audio_name
        output_file_path.mkdir(parents=True, exist_ok=True)

        # Write to file
        with open(
            output_file_path / f"{audio_name}_concatenated_text.txt", "w"
        ) as file:
            file.write(concatenated_text)

    def export_speakers_text_file(self, audio_name: str, group):
        # Sort the group by segment_num, if it's not already sorted
        group = group.sort_values("segment_num")

        # Initialize variables
        current_speaker = None
        formatted_text = ""
        current_speaker_text = []

        for _, row in group.iterrows():
            speaker_id = row["speaker_id"]
            text = row["text"]

            # If speaker_id is null, use the current speaker, or default to 0 if it's the first segment
            speaker_id = (
                speaker_id
                if pd.notnull(speaker_id)
                else (current_speaker if current_speaker else 0)
            )

            # If the speaker has changed or it's the first segment, append the current speaker's text to formatted_text
            if current_speaker is not None and current_speaker != speaker_id:
                formatted_text += f'SPEAKER {int(current_speaker + 1)}: {" ".join(current_speaker_text)}\n\n'
                current_speaker_text = (
                    []
                )  # Reset current_speaker_text for the new speaker

            current_speaker = speaker_id  # Update the current speaker
            current_speaker_text.append(
                text
            )  # Append the text to the current speaker's text

        # Append the last speaker's text
        formatted_text += f'SPEAKER {int((current_speaker or 0) + 1)}: {" ".join(current_speaker_text)}\n'

        output_file_path = self.output_folder / audio_name
        output_file_path.mkdir(parents=True, exist_ok=True)

        # Write to file
        with open(output_file_path / f"{audio_name}_by_speaker.txt", "w") as file:
            file.write(formatted_text)

    def export_textgrid_file(self, audio_name: str, group):
        # Create a new TextGrid object
        tg = textgrid.TextGrid(
            name=audio_name, minTime=0, maxTime=group["audio_duration"].iloc[0]
        )

        # Group by speaker_id
        speaker_groups = group.groupby("speaker_id", sort=False)

        for speaker_id, speaker_group in speaker_groups:
            # Corrected line: get xmax from the max end_time of the speaker_group
            tier = textgrid.IntervalTier(
                name=f"SPEAKER {int(speaker_id)}"
                if pd.notnull(speaker_id)
                else "SPEAKER 1",
                minTime=0,
                maxTime=speaker_group["end_time"].max(),
            )

            for _, row in speaker_group.iterrows():
                interval = textgrid.Interval(
                    row["start_time"], row["end_time"], row["text"]
                )
                # Add an interval for each segment
                tier.addInterval(interval)

            # Add the tier to the TextGrid
            tg.append(tier)

        output_file_path = self.output_folder / audio_name
        output_file_path.mkdir(parents=True, exist_ok=True)

        # Write the TextGrid to a file
        with open(output_file_path / f"{audio_name}.textgrid", "w") as file:
            tg.write(file)

    def export_original_audios(
        self,
        audios: pd.DataFrame,
        folder_ids: List[str],
        filter_format: AudioFormat,
        sample_rate: int,
        target_formats: List[AudioFormat],
    ):
        storage_client = GoogleDriveClient()

        for _, row in audios.iterrows():
            audio_name = row["name"]

            # Get the audio file from Google Drive
            audio_file = storage_client.search_file_in_folders(
                audio_name, folder_ids, filter_format
            )

            if audio_file is None:
                logger.warning(
                    f"Audio {audio_name} not found in GoogleDrive provided folders. Skipping."
                )
                continue

            # Load the audio file
            audio = AudioLoaderService(storage_client).load_audio(
                audio_file, sample_rate, mono_channel=True, normalize=False
            )

            output_file_path = self.output_folder / audio_name
            output_file_path.mkdir(parents=True, exist_ok=True)

            # Convert the audio file to the target formats
            for target_format in target_formats:
                sf.write(
                    output_file_path / f"{audio_name}.{target_format.value}",
                    audio.bytes,
                    sample_rate,
                )
