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
from sshtunnel import SSHTunnelForwarder


from src.steps import transcribe_audio, diarize_audio, AudioLoaderGoogleDrive
from src.utils import google_drive, logger as lg, database as db
from src.utils.scp_transfer import ssh, scp
from src.config import CONFIG

locale.getpreferredencoding = lambda: "UTF-8"

logger = lg.logger
logger.setLevel(level=DEBUG)

# Load whisper model
device = "cuda" if torch.cuda.is_available() else "cpu"
batch_size = 8
compute_type = "float16"

WHISPER_MODEL = "large-v2"
logger.info(f"Loading whisper model {WHISPER_MODEL}")
whisperx_model = whisperx.load_model(WHISPER_MODEL, device, compute_type=compute_type, language = 'pt')

dataset = 'nurc_sp'
CORPUS_ID = 2 # 1: MUPE, 2: NURC-SP

DATA_PATH = Path("./data/")
TEMP_DATA_PATH = DATA_PATH / "temp"
PROCESSED_DATA_PATH = DATA_PATH / "processed"

for path in (TEMP_DATA_PATH, PROCESSED_DATA_PATH):
    path.mkdir(parents=True, exist_ok=True)


logger.info(f"Stablishing Google Drive connection")
google_drive_service = google_drive.setup_service()

folders_to_explore = {
    "EF": {
        "folder_id": "1ndi8t_7shb3FB77ZTWd7xVW9KgLm6NLA",
    },
    "DID": {
        "folder_id": "1npveVhN9h5fsWhJzVKDUD7uQv76MNZ4i",
    },
    "D2": {
        "folder_id": "1njSedHukKrN8zJGM12eL-rt3aaOZpxdO",
    },
}


TEMP_WAV_AUDIO_PATH = TEMP_DATA_PATH / "temp_audio.wav"

ssh_tunnel: SSHTunnelForwarder = db.open_ssh_tunnel()
db_connection = db.mysql_connect(ssh_tunnel)

for folder_name, folder in folders_to_explore.items():

    logger.info(f"Exploring folder {folder_name}")
    OUTPUT_PATH = PROCESSED_DATA_PATH / folder_name

    files_in_folder  = google_drive.get_files_from_folder(folder["folder_id"])
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

        file_name = os.path.splitext(item['name'])[0]
        file_name = file_name.replace("_sem_cabecalho", "").replace("_sem_cabecallho", "").replace("_sem_cabeçalho", "")
        
        audios_with_name = db.get_audios_by_name(db_connection, file_name)
        # If there is already an audio on the database (shape > 0), we shouldn't process it again.
        if audios_with_name.shape[0] > 0:
            continue

        logger.info(f"Creating audio {file_name} on database")
        audio_id = db.add_audio(db_connection, file_name, CORPUS_ID)

        subdataset = folder_name
        audio_drive_id = item["id"]
        audio_path = item["name"]

        OUTPUT_PATH = PROCESSED_DATA_PATH / folder_name / file_name
        OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
        output_audio_folder = Path(OUTPUT_PATH / "audios")
        output_audio_folder.mkdir(parents=True, exist_ok=True)

        output_transcription_folder = Path(OUTPUT_PATH / "transcriptions")
        output_transcription_folder.mkdir(parents=True, exist_ok=True)

        logger.debug("Loading file from Google Drive")
        audio = AudioLoaderGoogleDrive(google_drive_service).load_and_downsample(audio_drive_id)
        sf.write(TEMP_WAV_AUDIO_PATH, audio, 16000)

        logger.debug(f"File loaded and saved locally to {TEMP_WAV_AUDIO_PATH}")

        logger.debug("Transcribing audio")
        audio = whisperx.load_audio(TEMP_WAV_AUDIO_PATH)
        result = whisperx_model.transcribe(audio, batch_size=batch_size)

        logger.debug("Aligning audio")
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
        result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

        audio_duration = 0
        for i, segment in enumerate(result["segments"]):
            try:
                start_time = segment["start"]
                end_time = segment["end"]
                speaker_id = segment["speaker"].split("_")[-1] if "speaker" in segment else None

                transc_path = os.path.join(output_transcription_folder, f'{i:04}_{file_name}_{start_time}_{end_time}.txt')
                transcription = segment['text']
                with open(transc_path, "w", encoding="utf-8") as f:
                    f.write(transcription)

                audio_path = os.path.join(output_audio_folder, f'{i:04}_{file_name}_{start_time}_{end_time}.wav')
                audio_segment = AudioSegment.from_wav(TEMP_WAV_AUDIO_PATH)[int(start_time * 1000):int(end_time * 1000)]
                audio_segment.export(audio_path, format="wav")

                audio_path = audio_path.replace("/processed/", f"/{dataset}/")
                data['audio_name'].append(file_name)
                data['audio_segment_path'].append(audio_path)
                data['start'].append(start_time)
                data['end'].append(end_time)
                data['whisper_transcription'].append(transcription)
                data['transcription_path'].append(transc_path)
                data['speaker_id'].append(speaker_id)


                audio_duration = end_time
                duration = end_time - start_time
                frames = int(duration * 16000)
                duration = int(duration)

                db.add_audio_segment(db_connection, audio_path, transcription, audio_id, i, frames, duration, start_time, end_time, speaker_id)

            except Exception as e:
                logger.error(f"Erro ao processar segmento {file_name}: {e}")
                continue

        db.update_audio_duration(db_connection, audio_id, audio_duration)
        # Copy the files/directory recursively
        scp.put(audio_path, '~/BrazSpeechData/static/Dataset/data/nurc_sp/DID')
    
        df = pd.DataFrame(data)
        df.to_csv(OUTPUT_PATH / "summary.csv", index=False, encoding='utf-8', sep='|', mode='w')

db.mysql_disconnect(db_connection)
db.close_ssh_tunnel(ssh_tunnel)

# Close the SCP and SSH clients
scp.close()
ssh.close()