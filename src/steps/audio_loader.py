import librosa
import io
import numpy as np
from typing import Optional, Union, Tuple, Literal
from googleapiclient.http import MediaIoBaseDownload
import tempfile
import subprocess
import os

from src.utils.exceptions import EmptyAudio
from src.utils.logger import logger


class AudioLoaderGoogleDrive():

    def __init__(self, service, sample_rate: int = 16000, mono_channel: bool = True) -> None:
        self.google_drive_service = service
        self.sample_rate = sample_rate
        self.mono_channel = mono_channel
        
    def load_and_downsample(self, file_id: str, format: Literal[".wav", ".mp4"] = ".wav") -> np.ndarray:
        
        if format == ".wav":
            audio, sampling_rate =  librosa.load(self.get_file_content(file_id), sr=self.sample_rate, mono=self.mono_channel)
        elif format == ".mp4":
            audio, sampling_rate = self.get_audio_from_mp4(file_id, format)
        
        assert sampling_rate == self.sample_rate, "Couldn't read audio with desired sampling rate."

        audio, _ = librosa.effects.trim(audio, top_db=20)
        peak = np.abs(audio).max()
        if peak > 1.0:
            audio = 0.98 * audio / peak
        
        return audio

    def get_audio_from_mp4(self, file_id: str, format: Literal[".wav", ".mp4"]) -> Tuple[np.ndarray, float]:
        file_content = self.get_file_content(file_id)
        
        # Write the MP4 content to a temporary file and process with ffmpeg
        with tempfile.NamedTemporaryFile(suffix=format) as temp_file:
            temp_file.write(file_content.getvalue())
            temp_file.flush()

            # Process the MP4 file with ffmpeg and write the audio to a WAV file
            audio_filename = f"{temp_file.name}_audio.wav"
            result = subprocess.run(["ffmpeg", "-i", temp_file.name, "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", audio_filename])
            if result.returncode != 0:
                raise Exception('Error converting MP4 file to WAV using ffmpeg')
        
        # Load the audio file with librosa
        audio, sampling_rate = librosa.load(audio_filename, sr=self.sample_rate, mono=self.mono_channel)

        # Remove the generated audio file (WAV) if necessary
        os.remove(audio_filename)
        
        return audio, sampling_rate

    def get_file_content(self, file_id: str) -> io.BytesIO:
        request = self.google_drive_service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()

        downloader = MediaIoBaseDownload(file_content, request)

        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return io.BytesIO(file_content.getvalue())