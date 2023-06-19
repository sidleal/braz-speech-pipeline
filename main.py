import typer

app = typer.Typer(
    no_args_is_help=True,
    help="Run data pipelines for diarization, transcription, metadata extraction for feeding the BrazSpeechData platform.",
)


@app.command(name="nurc")
def nurc():
    from src.pipelines.diarize_and_transcribe_nurc import diarize_and_transcribe_nurc

    diarize_and_transcribe_nurc()


if __name__ == "__main__":
    app()