from pydantic import BaseModel
from typing import Optional, Dict, List

# Standard config (if you have special settings for your models, otherwise skip it)
class StandardModelConfig:
    orm_mode = True
    allow_population_by_field_name = True

class Meeting(BaseModel):
    id: str
    properties: Dict[str, Dict[str, Dict[str, List[Dict[str, Dict[str, str]]]]]]
    jumpshare_link: Optional[str]

class Transcription(BaseModel):
    content: str

class JumpshareLink(BaseModel):
    url: str

class NotionBlock:
    object: str
    type: str
    paragraph: Optional[Dict[str, List[Dict[str, str]]]] = None
    toggle: Optional[Dict[str, List[Dict[str, str]]]] = None

class ToggleBlock:
    object: str
    type: str
    toggle: Dict[str, List[Dict[str, str]]]