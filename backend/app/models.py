from pydantic import BaseModel
from typing import Optional

# Standard config (if you have special settings for your models, otherwise skip it)
class StandardModelConfig:
    orm_mode = True
    allow_population_by_field_name = True

# Define TranscriptionRequest model
class TranscriptionRequest(BaseModel):
    transcription: Optional[str] = None

    class Config(StandardModelConfig):
        schema_extra = {
            "example": {
                "transcription": "This is an example transcription."
            }
        }

# Define TranscriptionResponse model
class TranscriptionResponse(BaseModel):
    transcription: str

    class Config(StandardModelConfig):
        schema_extra = {
            "example": {
                "transcription": "This is the transcribed text."
            }
        }

# Define any other models you need
class HelloWorldResponse(BaseModel):
    message: str

    class Config(StandardModelConfig):
        schema_extra = {
            "example": {
                "message": "Hello, world!"
            }
        }
