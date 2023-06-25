import typer
from src.pipelines.diarize_and_transcribe import diarize_and_transcribe

app = typer.Typer(
    no_args_is_help=True,
    help="Run data pipelines for diarization, transcription, metadata extraction for feeding the BrazSpeechData platform.",
)

@app.command(name="hello")
def hello():
    print("Hello, world!")
    
@app.command(name="mupe")
def mupe():
    dataset = 'mupe'
    CORPUS_ID = 1 # 1: MUPE, 2: NURC-SP
    
    folders_to_explore = {
        "MUPE": {
            "folder_id": "1cjSMGV1w5WEOGgt2fPC3C2bPZLUZ2saF",
        }
    }
    format = ".mp4"
    diarize_and_transcribe(dataset, CORPUS_ID, folders_to_explore, format)
    
@app.command(name="nurc")
def nurc():
    from src.pipelines.diarize_and_transcribe_nurc import diarize_and_transcribe_nurc

    diarize_and_transcribe_nurc()


if __name__ == "__main__":
    app()