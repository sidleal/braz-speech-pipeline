from pydantic import BaseModel


class Segment(BaseModel):
    segment_path: str
    text_asr: str
    audio_id: int
    segment_num: int
    frames: int
    duration: int
    start_time: float
    end_time: float
    speaker_id: int