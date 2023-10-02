import whisperx
from whisperx.types import (
    SingleAlignedSegment,
    TranscriptionResult,
    AlignedTranscriptionResult,
)
from whisperx.asr import FasterWhisperPipeline
from typing import Literal, List
import torch

from src.utils.logger import logger
from src.config import CONFIG
from src.models.audio import Audio
from src.models.segment import Segment


class SegmentWithSpeaker(SingleAlignedSegment):
    speaker: str


class TranscriptionService:
    def __init__(
        self,
        whisper_model: str = "large-v2",
        batch_size: int = 8,
        compute_type: str = "float16",
    ):
        self.device: Literal["cuda", "cpu"] = (
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        logger.info(f"Loading whisper model {whisper_model}")
        self.whisperx_model: FasterWhisperPipeline = whisperx.load_model(
            whisper_model, self.device, compute_type=compute_type, language="pt"
        )
        self.batch_size: int = batch_size
        self.compute_type: str = compute_type

    def transcribe(self, audio: Audio) -> List[Segment]:
        # TODO: evaluate if it is better to use a temporary file or not
        # logger.debug("Loading audio")
        # audio = whisperx.load_audio(audio_name)

        logger.debug("Transcribing audio")
        transcription_result: TranscriptionResult = self.whisperx_model.transcribe(
            audio.trimmed_audio, batch_size=self.batch_size
        )

        logger.debug("Aligning audio")
        model_a, metadata = whisperx.load_align_model(
            language_code=transcription_result["language"], device=self.device
        )
        align_result: AlignedTranscriptionResult = whisperx.align(
            iter(transcription_result["segments"]),
            model_a,
            metadata,
            audio.trimmed_audio,
            self.device,
            return_char_alignments=False,
        )

        logger.debug("Diarization audio with PyAnnote")
        # 3. Assign speaker labels
        diarize_model = whisperx.DiarizationPipeline(
            use_auth_token=CONFIG.pyannote.auth_token, device=self.device
        )

        # # add min/max number of speakers if known
        # diarize_segments = diarize_model(audio_file)
        diarize_segments = diarize_model(
            audio.trimmed_audio, min_speakers=1, max_speakers=4
        )

        result = whisperx.assign_word_speakers(diarize_segments, align_result)
        resulted_segments: List[SegmentWithSpeaker] = result["segments"]

        segments = [
            Segment(
                segment_num=idx,
                start_time=s["start"],
                end_time=s["end"],
                speaker=s["speaker"].split("_")[-1] if "speaker" in s else None,
                text_asr=s["text"],
                sample_rate=audio.sample_rate,
            )
            for idx, s in enumerate(resulted_segments)
        ]

        return segments
