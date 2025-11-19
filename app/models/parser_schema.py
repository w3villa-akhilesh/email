from pydantic import BaseModel, Field
from typing import Optional, List

class ResumeParserPayloadKivo(BaseModel):
    resume_url: str
    applied_job_title: Optional[str] = None
    applied_job_keywords: Optional[List[str]] = None  # Making this field optional
    min_experience: Optional[int] = None  # Minimum years of experience required for the job
    max_experience: Optional[int] = None  # Maximum years of experience required for the job
    email: Optional[str] = None
 
class JobProfileUpdatePayload(BaseModel):
    id: int
    title: str
    jd: str = Field(..., alias="jd")