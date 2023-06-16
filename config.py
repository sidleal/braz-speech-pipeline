from pydantic import BaseModel, BaseSettings

# MySQL connection details
class MySQL(BaseModel):
    host: str
    port: int
    username: str
    password: str
    database: str

class Config(BaseSettings):
    mysql: MySQL
    
    class Config:
        env_file = ".env", "../.env", "../../.env"
        env_file_encoding = "utf-8"
        env_nested_delimiter = "__"
        
CONFIG = Config()

__all__ = ["CONFIG"]