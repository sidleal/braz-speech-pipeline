from pydantic import BaseModel
from typing import Optional


class Segment(BaseModel):
    text_asr: str
    segment_num: int
    sample_rate: int
    start_time: float
    end_time: float
    speaker: Optional[str]

    @property
    def duration(self):
        return self.end_time - self.start_time

    @property
    def int_duration(self):
        return int(self.duration)

    @property
    def frames(self):
        return int(self.duration * self.sample_rate)


class SegmentCreate(Segment):
    segment_path: str
    original_start_time: float
    original_end_time: float
    speaker_id: int
    segment_name: str
    extension: str


class SegmentCreateInDB(SegmentCreate):
    audio_id: int
