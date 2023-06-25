import typer
from pathlib import Path

from src.pipelines.diarize_and_transcribe import diarize_and_transcribe


app = typer.Typer(
    no_args_is_help=True,
    help="Run data pipelines for diarization, transcription, metadata extraction for feeding the BrazSpeechData platform.",
)

DATA_PATH = Path("./data/")

@app.command(name="mupe")
def mupe():
    CORPUS_ID = 1
    
    folders_to_explore = {
        "mupe": {
            "folder_id": "1cjSMGV1w5WEOGgt2fPC3C2bPZLUZ2saF",
        }
    }
    format = ".mp4"
    diarize_and_transcribe(DATA_PATH, CORPUS_ID, folders_to_explore, format, lambda x: "_".join(x.split("_")[:3]))
    
@app.command(name="nurc")
def nurc():
    CORPUS_ID = 2
    
    folders_to_explore = {
        "nurc_sp/EF": {
            "folder_id": "1ndi8t_7shb3FB77ZTWd7xVW9KgLm6NLA",
        },
        "nurc_sp/DID": {
            "folder_id": "1npveVhN9h5fsWhJzVKDUD7uQv76MNZ4i",
        },
        "nurc_sp/D2": {
            "folder_id": "1njSedHukKrN8zJGM12eL-rt3aaOZpxdO",
        },
    }
    format = ".wav"
    
    diarize_and_transcribe(DATA_PATH, CORPUS_ID, folders_to_explore, format)


if __name__ == "__main__":
    app()