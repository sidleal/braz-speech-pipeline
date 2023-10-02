import librosa
import io
import numpy as np
from typing import Optional, Union, Tuple, Literal
from googleapiclient.http import MediaIoBaseDownload
import tempfile
import subprocess
import os

from src.utils.exceptions import EmptyAudio
from src.clients.storage_base import BaseStorage
from src.models.audio import Audio
from src.models.file import File


class AudioLoaderService:
    def __init__(self, repository_client: BaseStorage) -> None:
        self.remote = repository_client
        pass

    def load_audio(
        self,
        file: File,
        sample_rate: int,
        mono_channel: bool,
    ) -> Audio:
        if file._extension == ".wav" or file._extension == ".mp3":
            audio_ndarray, loaded_sampling_rate = librosa.load(
                self.remote.get_file_content(file.id),
                sr=sample_rate,
                mono=mono_channel,
            )
        elif file._extension == ".mp4":
            audio_ndarray, loaded_sampling_rate = self.__get_audio_from_mp4(
                file.id, file._extension, sample_rate, mono_channel
            )
        else:
            raise ValueError("Invalid audio format.")

        assert (
            loaded_sampling_rate == sample_rate
        ), "Couldn't read audio with desired sampling rate."

        _, non_silent_indexes = librosa.effects.trim(audio_ndarray, top_db=20)
        peak = np.abs(audio_ndarray).max()
        if peak > 1.0:
            audio_ndarray = 0.98 * audio_ndarray / peak

        return Audio(
            name=file.name,
            bytes=audio_ndarray,
            sample_rate=int(loaded_sampling_rate),
            non_silent_interval=non_silent_indexes,
        )

    def __get_audio_from_mp4(
        self,
        file_id: str,
        format: Literal[".wav", ".mp4"],
        sample_rate: int,
        mono_channel: bool,
    ) -> Tuple[np.ndarray, float]:
        file_content = self.remote.get_file_content(file_id)

        # Write the MP4 content to a temporary file and process with ffmpeg
        with tempfile.NamedTemporaryFile(suffix=format) as temp_file:
            temp_file.write(file_content.getvalue())
            temp_file.flush()

            # Process the MP4 file with ffmpeg and write the audio to a WAV file
            audio_filename = f"{temp_file.name}_audio.wav"
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    temp_file.name,
                    "-vn",
                    "-acodec",
                    "pcm_s16le",
                    "-ar",
                    f"{sample_rate}",
                    "-ac",
                    f"{1 if mono_channel else 2}",
                    audio_filename,
                ]
            )
            if result.returncode != 0:
                raise EmptyAudio("Error converting MP4 file to WAV using ffmpeg")

        # Load the audio file with librosa
        audio, sampling_rate = librosa.load(
            audio_filename, sr=sample_rate, mono=mono_channel
        )

        # Remove the generated audio file (WAV) if necessary
        os.remove(audio_filename)

        return audio, sampling_rate
