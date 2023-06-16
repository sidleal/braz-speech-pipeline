def transcribe_audio(audio_path: str, whisper_model) -> str:
    transcription_result = whisper_model.transcribe(audio_path)
    return str(transcription_result["text"])