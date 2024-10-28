from pydantic import BaseModel
from typing import Optional, Dict, List

# Standard config (if you have special settings for your models, otherwise skip it)
class StandardModelConfig:
    orm_mode = True
    allow_population_by_field_name = True

class Transcription(BaseModel):
    content: str

class NotionBlock:
    object: str
    type: str
    paragraph: Optional[Dict[str, List[Dict[str, str]]]] = None
    toggle: Optional[Dict[str, List[Dict[str, str]]]] = None

class ToggleBlock:
    object: str
    type: str
    toggle: Dict[str, List[Dict[str, str]]]

class JumpshareLink(BaseModel):
    url: str