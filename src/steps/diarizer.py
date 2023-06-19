import sys 
import os
from scipy.io import wavfile 
from pyannote.audio import Pipeline
from typing import Optional
import os

from src.config import CONFIG


def diarize_audio(audio_path, out_dir, num_speakers=None, audio_name: Optional[str] = None, keep_turn=False, min_sec=0.5, max_sec=None):

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization",
        use_auth_token=CONFIG.pyannote.auth_token
    )

    sr, audio = wavfile.read(audio_path)
    diarization = pipeline(audio_path, num_speakers=num_speakers)
    
    start_frames, end_frames = None, None
    last_spk = None
    i = 0
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        spk = speaker   
        if out_dir is None:
            out_dir = spk
        os.makedirs(out_dir, exist_ok=True)

        print(f"start={turn.start:.1f}s stop={turn.end:.1f}s speaker: {spk}")
        
        if keep_turn:
            if not start_frames:
                start_frames = int(turn.start)
            if not last_spk:
                last_spk = spk
            if spk == last_spk:
                end_frames = int(sr*turn.end)
            else:
                i+=1
                if min_sec is not None and (end_frames - start_frames)/sr < min_sec:
                    print(f"skipping {turn.start:.1f}s stop={turn.end:.1f} because it is too short")
                    continue
                if max_sec is not None and (end_frames - start_frames)/sr > max_sec:
                    print(f"skipping {turn.start:.1f}s stop={turn.end:.1f} because it is too long")
                    continue
                
                wavfile.write(os.path.join(out_dir, f"{i:04}-{last_spk}.wav"), sr, audio[start_frames:end_frames])

                last_spk = spk
                start_frames = int(sr*turn.start)
                end_frames = int(sr*turn.end)
        else:
            segment_num = f"{i:04}"
            speaker_name = str(spk)
            start_time = str(turn.start)
            end_time = str(turn.end)

            output_file_name = "-".join(
                [attr for attr in [
                    segment_num,
                    audio_name,
                    start_time,
                    end_time,
                    speaker_name
                ] if attr is not None]
            )
            output_file_name += ".wav"
            wavfile.write(os.path.join(out_dir, output_file_name), sr, audio[int(sr*turn.start):int(sr*turn.end)])
            i+=1