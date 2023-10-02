from typing import Optional


def get_mime_from_extension(extension) -> Optional[str]:
    try:
        mime = {
            "wav": "audio/wav",
            "mp3": "audio/mp3",
            "mp4": "video/mp4",
            "txt": "text/plain",
            "doc": "application/vnd.google-apps.document",
            "xls": "application/vnd.google-apps.spreadsheet",
            "ppt": "application/vnd.google-apps.presentation",
            "pdf": "application/pdf",
            "jpg": "image/jpeg",
            "png": "image/png",
            "txt": "text/plain",
        }[extension]
        return mime
    except KeyError:
        print(f"Invalid extension {extension}")
        return None
