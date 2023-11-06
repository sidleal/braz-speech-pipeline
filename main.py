import typer
from pathlib import Path
from typing import Literal, Optional, List

from src.pipelines.diarize_and_transcribe import diarize_and_transcribe
from src.pipelines.transcribe import transcribe_audios_in_folder
from src.pipelines.export import export_corpus_dataset

from src.clients.scp_transfer import FileTransfer
from src.clients.database import Database

from src.models.file import AudioFormat

app = typer.Typer(
    no_args_is_help=True,
    help="Run data pipelines for diarization, transcription, metadata extraction for feeding the BrazSpeechData platform.",
)

DATA_PATH = Path("./data/")


@app.command(name="export")
def export(
    corpus_id: int = typer.Option(..., help="Corpus ID"),
    output_folder: Path = typer.Option(DATA_PATH / "export", help="Output folder"),
    csv: bool = typer.Option(False, help="Export to CSV"),
    textgrid: bool = typer.Option(False, help="Export to TextGrid"),
    continuous_text: bool = typer.Option(False, help="Export to continuous text"),
    speakers_text: bool = typer.Option(False, help="Export to speakers text"),
    original_audios: bool = typer.Option(False, help="Export original audios"),
    google_drive_folder_ids: Optional[List[str]] = typer.Option(
        None, help="Google Drive folder IDs"
    ),
    filter_format: Optional[AudioFormat] = typer.Option(
        None, help="Filter audios by format"
    ),
    sample_rate: int = typer.Option(48000, help="Sample rate"),
    all: bool = typer.Option(False, help="Export all"),
    debug: bool = typer.Option(False, help="Debug mode"),
):
    if all:
        csv = True
        textgrid = True
        continuous_text = True
        speakers_text = True
        original_audios = True

    with Database() as db:
        export_corpus_dataset(
            corpus_id=corpus_id,
            output_folder=output_folder,
            db=db,
            export_original_audios=original_audios,
            google_drive_folder_ids=google_drive_folder_ids,
            sample_rate=sample_rate,
            filter_format=filter_format,
            export_concanated_text=continuous_text,
            export_speakers_text=speakers_text,
            export_text_grid=textgrid,
            export_to_csv=csv,
            debug=debug,
        )


@app.command(name="transcribe")
def transcribe(
    corpus_id: int = typer.Option(..., help="Corpus ID"),
    folder_id: str = typer.Option(
        ..., help="Google Drive folder ID that contains the audios to transcribe"
    ),
    output_folder: Path = typer.Option(DATA_PATH, help="Output folder"),
    storage_output_folder_id: str = typer.Option(
        None,
        help="Google Drive folder ID to save the transcriptions. If none is provided, the transcriptions will be saved in the same folder as the audios.",
    ),
    format_filter: Optional[AudioFormat] = typer.Option(
        None, help="Filter audios by format"
    ),
    save_to_db: bool = typer.Option(False, help="Save transcriptions to database"),
    save_to_drive: bool = typer.Option(
        False, help="Save transcriptions to Google Drive"
    ),
    transfer_to_server: bool = typer.Option(
        False, help="Transfer transcriptions to server"
    ),
):
    get_db_search_key = lambda x: x

    # Handle MUPE special case:
    if corpus_id == 1:
        format_filter = AudioFormat.MP4
        get_db_search_key = lambda x: "_".join(x.split("_")[:3])
    elif corpus_id == 2:
        format_filter = AudioFormat.WAV

    with FileTransfer() as ft:
        with Database() as db:
            transcribe_audios_in_folder(
                corpus_id=corpus_id,
                folder_id=folder_id,
                output_folder=output_folder,
                db=db if save_to_db else None,
                storage_output_folder_id=storage_output_folder_id,
                format_filter=format_filter,
                file_transfer_client=ft if transfer_to_server else None,
                save_to_drive=save_to_drive,
                get_db_search_key=get_db_search_key,
            )


@app.command(name="mupe")
def mupe():
    CORPUS_ID = 1

    folders_to_explore = {
        "mupe": {
            "folder_id": "1cjSMGV1w5WEOGgt2fPC3C2bPZLUZ2saF",
        }
    }
    format = ".mp4"
    diarize_and_transcribe(
        DATA_PATH,
        CORPUS_ID,
        folders_to_explore,
        format,
        lambda x: "_".join(x.split("_")[:3]),
    )


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


@app.command(name="run")
def run_folder(dataset_name: str, folder_id: str, corpus_id: int, format):
    folders_to_explore = {dataset_name: {"folder_id": folder_id}}
    diarize_and_transcribe(DATA_PATH, corpus_id, folders_to_explore, format)


if __name__ == "__main__":
    app()
