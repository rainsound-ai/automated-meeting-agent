import json
from pydantic import BaseModel
from app.lib.Pydantic import standard_model_config

# Define TranscriptionRequest model
class TranscriptionRequest(BaseModel):
    transcription: str

    model_config = standard_model_config

# Define TranscriptionResponse model
class TranscriptionResponse(BaseModel):
    transcription: str

    model_config = standard_model_config

# Define other API types and include the new ones
class HelloWorldResponse(BaseModel):
    message: str

    model_config = standard_model_config

class ApiTypes(BaseModel):
    hello_world_response: HelloWorldResponse
    transcription_request: TranscriptionRequest
    transcription_response: TranscriptionResponse

    model_config = standard_model_config

# Function to save the schema as JSON
def save_all():
    model_schema = ApiTypes.model_json_schema()
    file_name = "../frontend/src/lib/ApiTypes.json"
    with open(file_name, "w") as f:
        json.dump(model_schema, f, indent=2)

