from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import Optional


class Pyannote(BaseModel):
    auth_token: str


# SSH connection details
class SSHTunnel(BaseModel):
    host: str
    port: int
    username: str
    password: str


# MySQL connection details
class MySQL(BaseModel):
    host: str
    port: int
    username: str
    password: str
    database: str
    use_ssh: bool = True


class RemoteMachine(BaseModel):
    dataset_path: str = "/home/utf/BrazSpeechData/static/Dataset"


class Computation(BaseModel):
    batch_size: int = 8
    compute_type: str = "float16"
    whisper_model: str = "large-v3"


class Config(BaseSettings):
    pyannote: Pyannote
    sshtunnel: SSHTunnel
    mysql: MySQL
    remote: RemoteMachine = RemoteMachine()
    sample_rate: int = 16000
    mono_channel: bool = True
    computation: Computation = Computation()

    class Config:
        env_file = ".env", "../.env", "../../.env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"


CONFIG = Config()

__all__ = ["CONFIG"]
