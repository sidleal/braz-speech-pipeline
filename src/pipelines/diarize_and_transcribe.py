from pathlib import Path
from logging import DEBUG
import soundfile as sf
from dotenv import load_dotenv
import torch
from tqdm import tqdm
import locale
import os
import pandas as pd
from pydub import AudioSegment
import whisperx
from tqdm import tqdm
from typing import Literal

from src.steps import AudioLoaderGoogleDrive
from src.utils import google_drive, logger as lg
from src.utils.database import Database
from src.utils.scp_transfer import FileTransfer
from src.config import CONFIG

locale.getpreferredencoding = lambda: "UTF-8"


logger = lg.logger
logger.setLevel(level=DEBUG)

# Load whisper model
device = "cuda" if torch.cuda.is_available() else "cpu"
batch_size = 8
compute_type = "float16"
WHISPER_MODEL = "large-v2"

DATA_PATH = Path("./data/")
TEMP_DATA_PATH = DATA_PATH / "temp"
PROCESSED_DATA_PATH = DATA_PATH / "processed"

TEMP_WAV_AUDIO_PATH = TEMP_DATA_PATH / "temp_audio.wav"

for path in (TEMP_DATA_PATH, PROCESSED_DATA_PATH):
    path.mkdir(parents=True, exist_ok=True)


def diarize_and_transcribe(dataset, corpus_id, folders_to_explore, format: Literal[".wav", ".mp4"]):
    with Database() as db:
        
        logger.info(f"Loading whisper model {WHISPER_MODEL}")
        whisperx_model = whisperx.load_model(WHISPER_MODEL, device, compute_type=compute_type, language = 'pt')

        logger.info(f"Stablishing Google Drive connection")
        google_drive_service = google_drive.setup_service()

        for folder_name, folder in folders_to_explore.items():

            logger.info(f"Exploring folder {folder_name}")
            OUTPUT_PATH = PROCESSED_DATA_PATH / folder_name

            files_in_folder  = google_drive.get_files_from_folder(folder["folder_id"], format)
            logger.info(f"On the folder {folder_name}, we have {len(files_in_folder)} audios.")

            for item in tqdm(files_in_folder):
                data = {
                    'audio_name': [],
                    'start': [],
                    'end': [],
                    'whisper_transcription': [],
                    'audio_segment_path': [],
                    'transcription_path': [],
                    'speaker_id': []
                }

                audio_name = os.path.splitext(item["name"])[0]
                video_code = "_".join(audio_name.split("_")[:3])
                
                audios_with_name = db.get_audios_by_name(video_code)
                # If there is already an audio on the database (shape > 0), we shouldn't process it again.
                if audios_with_name.shape[0] > 0:
                    continue
                
                logger.info(f"Processing audio {audio_name}.")

                audio_drive_id = item["id"]

                OUTPUT_PATH = PROCESSED_DATA_PATH / folder_name / audio_name
                OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
                output_audio_folder = Path(OUTPUT_PATH / "audios")
                output_audio_folder.mkdir(parents=True, exist_ok=True)

                output_transcription_folder = Path(OUTPUT_PATH / "transcriptions")
                output_transcription_folder.mkdir(parents=True, exist_ok=True)

                logger.debug("Loading file from Google Drive")
                audio = AudioLoaderGoogleDrive(google_drive_service).load_and_downsample(audio_drive_id, format)
                sf.write(TEMP_WAV_AUDIO_PATH, audio, 16000)

                logger.debug(f"File loaded and saved locally to {TEMP_WAV_AUDIO_PATH}")

                logger.debug("Transcribing audio")
                audio = whisperx.load_audio(TEMP_WAV_AUDIO_PATH)
                result = whisperx_model.transcribe(audio, batch_size=batch_size)

                logger.debug("Aligning audio")
                model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
                result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

                logger.debug("Diarization audio with PyAnnote")
                # 3. Assign speaker labels
                diarize_model = whisperx.DiarizationPipeline(use_auth_token=CONFIG.pyannote.auth_token, device=device)

                # add min/max number of speakers if known
                # diarize_segments = diarize_model(audio_file)
                diarize_segments = diarize_model(TEMP_WAV_AUDIO_PATH, min_speakers=1, max_speakers=4)

                result = whisperx.assign_word_speakers(diarize_segments, result)
                
                logger.info(f"Creating audio {audio_name} on database")
                audio_id = db.add_audio(audio_name, corpus_id)
                audio_duration = 0
                for i, segment in tqdm(enumerate(result["segments"])):
                    try:
                        start_time = segment["start"]
                        end_time = segment["end"]
                        speaker_id = segment["speaker"].split("_")[-1] if "speaker" in segment else None

                        transc_path = os.path.join(output_transcription_folder, f'{i:04}_{audio_name}_{start_time}_{end_time}.txt')
                        transcription = segment['text']
                        transcription = transcription.replace("'", "\'")
                        with open(transc_path, "w", encoding="utf-8") as f:
                            f.write(transcription)

                        segment_name = f'{i:04}_{audio_name}_{start_time}_{end_time}.wav'
                        segment_path_on_local = os.path.join(output_audio_folder, segment_name)
                        audio_segment = AudioSegment.from_wav(TEMP_WAV_AUDIO_PATH)[int(start_time * 1000):int(end_time * 1000)]
                        audio_segment.export(segment_path_on_local, format="wav")

                        segment_file_path_on_server = segment_path_on_local.replace("/processed/", f"/{dataset}/")
                        data['audio_name'].append(audio_name)
                        data['audio_segment_path'].append(segment_file_path_on_server)
                        data['start'].append(start_time)
                        data['end'].append(end_time)
                        data['whisper_transcription'].append(transcription)
                        data['transcription_path'].append(transc_path)
                        data['speaker_id'].append(speaker_id)


                        audio_duration = end_time
                        duration = end_time - start_time
                        frames = int(duration * 16000)
                        duration = int(duration)

                        db.add_audio_segment(segment_file_path_on_server, transcription, audio_id, i, frames, duration, start_time, end_time, speaker_id)
                        
                        # Copy the segment to NewHouse machine
                        with FileTransfer() as ft:

                            ft.put(
                                source=segment_path_on_local, 
                                target=f"{CONFIG.remote.dataset_path}/{segment_file_path_on_server}"
                            )
                        
                    except Exception as e:
                        logger.error(f"Erro ao processar segmento {segment_name}: {e}", stack_info=True)
                        continue

                db.update_audio_duration(audio_id, audio_duration)
                #TODO: add check to see if num of segments on DB is the same as the num of segments on target folder
                
                df = pd.DataFrame(data)
                df.to_csv(OUTPUT_PATH / "summary.csv", index=False, encoding='utf-8', sep='|', mode='w')