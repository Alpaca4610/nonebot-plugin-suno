from pydantic import Extra, BaseModel
from typing import Optional


class Config(BaseModel, extra=Extra.ignore):
    suno_token: Optional[str] = "" 

class ConfigError(Exception):
    pass