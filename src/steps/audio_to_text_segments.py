import os
import pandas as pd
from pathlib import Path
import soundfile as sf
import whisperx
from whisperx.types import SingleAlignedSegment, TranscriptionResult
from whisperx.asr import FasterWhisperPipeline
import tempfile
from pydub import AudioSegment
from typing import Literal, List, Any
import torch
from src.utils.database import Database
from src.utils.logger import logger
from src.config import CONFIG
from src.utils.scp_transfer import FileTransfer
from src.models.audio import Audio
from src.models.segment import Segment

class SegmentWithSpeaker(SingleAlignedSegment):
    speaker: str


class AudioToTextSegmentsConverter:
    def __init__(
        self,
        output_path: Path,
        whisperx_model: FasterWhisperPipeline,
        batch_size: int = 8,
        compute_type: str = "float16",
    ):
        output_path.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_PATH: Path = output_path
        self.whisperx_model: FasterWhisperPipeline = whisperx_model
        self.device: Literal["cuda", "cpu"] = (
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.batch_size: int = batch_size
        self.compute_type: str = compute_type

    def diarize_and_transcribe(self, audio: Audio, corpus_id: int):
        data = {
            "audio_name": [],
            "start": [],
            "end": [],
            "whisper_transcription": [],
            "audio_segment_path": [],
            "transcription_path": [],
            "speaker_id": [],
        }

        with Database() as db:
            with tempfile.NamedTemporaryFile(suffix=".wav") as temp_audio_file:
                # TODO: make sample rate as parameter
                sf.write(
                    temp_audio_file,
                    audio.trimmed_audio,
                    CONFIG.sample_rate,
                )

                logger.debug(f"File loaded and saved locally to {temp_audio_file.name}")

                segments = self._generate_text_segments(temp_audio_file.name)

                # logger.info(f"Creating audio {audio.name_with_no_spaces} on database")
                audio_id = db.add_audio(audio.name_with_no_spaces, corpus_id, audio.duration)

                self._save_segments(
                    audio_id, audio, segments, data, db, temp_audio_file
                )

                df = pd.DataFrame(data)
                df.to_csv(
                    self.OUTPUT_PATH / "summary.csv",
                    index=False,
                    encoding="utf-8",
                    sep="|",
                    mode="w",
                )

    def _generate_text_segments(self, audio_name) -> List[SegmentWithSpeaker]:
        logger.debug("Loading audio")
        audio = whisperx.load_audio(audio_name)

        logger.debug("Transcribing audio")
        transcription_result: TranscriptionResult = self.whisperx_model.transcribe(
            audio, batch_size=self.batch_size
        )

        logger.debug("Aligning audio")
        model_a, metadata = whisperx.load_align_model(
            language_code=transcription_result["language"], device=self.device
        )
        align_result = whisperx.align(transcription_result["segments"], model_a, metadata, audio, self.device, return_char_alignments=False)  # type: ignore

        logger.debug("Diarization audio with PyAnnote")
        # 3. Assign speaker labels
        diarize_model = whisperx.DiarizationPipeline(
            use_auth_token=CONFIG.pyannote.auth_token, device=self.device
        )

        # # add min/max number of speakers if known
        # diarize_segments = diarize_model(audio_file)
        diarize_segments = diarize_model(audio_name, min_speakers=1, max_speakers=4)

        result = whisperx.assign_word_speakers(diarize_segments, align_result)

        return result["segments"]

    def _save_segments(
        self,
        audio_id,
        audio: Audio,
        segments: List[SegmentWithSpeaker],
        data: "dict[str, list[Any]]",
        db: Database,
        temp_audio_file,
    ):
        output_audio_folder = Path(self.OUTPUT_PATH / "audios")
        output_transcription_folder = Path(self.OUTPUT_PATH / "transcriptions")

        for folder in (output_audio_folder, output_transcription_folder):
            folder.mkdir(parents=True, exist_ok=True)

        segment_name = "###"
        for i, segment in enumerate(segments):
            try:
                start_time = audio.start_offset_trimmed_audio + segment["start"]
                end_time = audio.start_offset_trimmed_audio + segment["end"]
                speaker_id = (
                    segment["speaker"].split("_")[-1] if "speaker" in segment else None
                )

                segment_name = f"{i:04}_{audio.name_with_no_spaces}_{start_time}_{end_time}"

                transc_path = os.path.join(
                    output_transcription_folder, f"{segment_name}.txt"
                )
                transcription = segment["text"]
                transcription = transcription.replace("'", "'")
                with open(transc_path, "w", encoding="utf-8") as f:
                    f.write(transcription)

                segment_path_on_local = os.path.join(
                    output_audio_folder, f"{segment_name}.wav"
                )
                audio_segment = AudioSegment.from_wav(temp_audio_file)[
                    int(start_time * 1000) : int(end_time * 1000)
                ]
                audio_segment.export(segment_path_on_local, format="wav")

                data["audio_name"].append(audio.name_with_no_spaces)
                data["audio_segment_path"].append(segment_path_on_local)
                data["start"].append(start_time)
                data["end"].append(end_time)
                data["whisper_transcription"].append(transcription)
                data["transcription_path"].append(transc_path)
                data["speaker_id"].append(speaker_id)

                duration = end_time - start_time
                frames = int(duration * 16000)
                duration = int(duration)

                audio_segment = Segment(
                    segment_path=segment_path_on_local,
                    text_asr=transcription,
                    audio_id=audio_id,
                    segment_num=i,
                    frames=frames,
                    duration=duration,
                    start_time=start_time,
                    end_time=end_time,
                    speaker_id=speaker_id if speaker_id is not None else -1,
                )
                
                db.add_audio_segment(audio_segment)

                # Copy the segment to NewHouse machine
                with FileTransfer() as ft:
                    ft.put(
                        source=segment_path_on_local,
                        target=os.path.join(
                            CONFIG.remote.dataset_path, segment_path_on_local
                        ),
                    )

            except Exception as e:
                logger.error(
                    f"Erro ao processar segmento {segment_name}: {e}", stack_info=True
                )
                continue
