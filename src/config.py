from pydantic import BaseModel, BaseSettings

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

class Config(BaseSettings):
    pyannote: Pyannote
    sshtunnel: SSHTunnel
    mysql: MySQL
    
    class Config:
        env_file = ".env", "../.env", "../../.env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        
CONFIG = Config()

__all__ = ["CONFIG"]