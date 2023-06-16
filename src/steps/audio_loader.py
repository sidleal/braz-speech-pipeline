import librosa
import io
import numpy as np
from typing import Optional, Union, Tuple
from googleapiclient.http import MediaIoBaseDownload

from src.utils.exceptions import EmptyAudio
from src.utils.logger import logger


class AudioLoaderGoogleDrive():

    def __init__(self, service, sample_rate: int = 16000, mono_channel: bool = True) -> None:
        self.google_drive_service = service
        self.sample_rate = sample_rate
        self.mono_channel = mono_channel
    
    def load_and_downsample(self, file_id: str) -> np.ndarray:
        audio, sampling_rate =  librosa.load(self.get_file_content(file_id), sr=self.sample_rate, mono=self.mono_channel)

        assert sampling_rate == self.sample_rate, "Couldn't read audio with desired sampling rate."

        audio, _ = librosa.effects.trim(audio, top_db=20)
        peak = np.abs(audio).max()
        if peak > 1.0:
            audio = 0.98 * audio / peak
        
        return audio

    def get_file_content(self, file_id: str) -> io.BytesIO:
        request = self.google_drive_service.files().get_media(fileId=file_id)
        file_content = io.BytesIO()

        downloader = MediaIoBaseDownload(file_content, request)

        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return io.BytesIO(file_content.getvalue())