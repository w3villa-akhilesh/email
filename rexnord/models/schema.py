from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal, Any
from google.genai import types
from google.genai.types import GenerateContentConfig

json_response_config = types.GenerationConfig(
            response_mime_type="application/json"
        )
# Generation configs for different use cases:

# For JSON responses - ensures output is in JSON format
json_response_config = types.GenerationConfig(
    response_mime_type="application/json"
)

# For controlled, focused responses with low variability
controlled_generation_config = GenerateContentConfig(
    temperature=0.1,  # Low temperature for more focused outputs
    top_p=0.5        # Moderate top_p for some controlled variation
)

# For balanced responses with moderate creativity
balanced_generation_config = GenerateContentConfig(
    temperature=0.5,  # Medium temperature balances focus and creativity
    top_p=0.9        # Higher top_p allows more diverse outputs
)

# For strict, deterministic responses
strict_generation_config = GenerateContentConfig(
    temperature=0.0,  # Zero temperature for deterministic output
    top_p=0.0        # Zero top_p for most likely completion only
)

class RexnordTriageAgentRequest(BaseModel):
    query: str  # Query to be processed by the rexnord agent
    query_id: str
    # Accept either a JSON string or an object; the endpoint normalizes to dict.
    profile_info: Dict[str, Any] | str

class ResponseFormat(BaseModel):
    text: str
    image_link: List[str] = Field(default_factory=list, description="List of image URLs, empty list if none")
    doc_link: List[str] = Field(default_factory=list, description="List of document URLs, empty list if none")
