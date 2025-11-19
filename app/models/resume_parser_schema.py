from pydantic import BaseModel, Field
from typing import Optional, List, Union

class JobKeyword(BaseModel):
    keyword: str
    weightage: int

class JobApplicantQNA(BaseModel):
    question: str
    answer: str

class EvaluationCriteria(BaseModel):
    parameter_name: str
    description: str
    level: str  # L0 (Basic) to L4 (Very Hard)

class JobProfileDetails(BaseModel):
    title: str
    job_description: str
    min_year: Optional[int] = None
    max_year: Optional[int] = None
    min_experience: Optional[int] = None  # Alternative field name for min_year
    max_experience: Optional[int] = None  # Alternative field name for max_year
    qualification: str
    location: str
    
    def get_min_experience(self) -> Optional[int]:
        """Get minimum experience, preferring min_experience over min_year."""
        return self.min_experience if self.min_experience is not None else self.min_year
    
    def get_max_experience(self) -> Optional[int]:
        """Get maximum experience, preferring max_experience over max_year."""
        return self.max_experience if self.max_experience is not None else self.max_year

class ResumeParserPayload(BaseModel):
    job_applicant_id:Optional[int] = None
    resume_url: str = None
    resume_text: Optional[str] = None  # Pre-extracted resume text to skip parsing
    applied_job_title: Optional[str] = None
    applied_job_keywords: Optional[List[JobKeyword]] = None  # Now a list of objects
    evaluation_criteria: Optional[List[EvaluationCriteria]] = None  # New field for evaluation criteria
    job_profile_details: Optional[JobProfileDetails] = None  # New field for job profile details
    job_applicant_filled_qna: Optional[List[JobApplicantQNA]] = None  # New field for QNA
    min_experience: Optional[int] = None  # Minimum years of experience required for the job
    max_experience: Optional[int] = None  # Maximum years of experience required for the job
    email: Optional[str] = None
    company_id: Union[str, int]
    origin: str
    resume_parser_access_token:Optional[str] = None
    rails_api_url: Optional[str] = None  # Kept for backward compatibility (not used)
    auth_token: Optional[str] = None  # Kept for backward compatibility (not used)
    enable_real_time_updates: Optional[bool] = False  # Kept for backward compatibility (not used)
    resume_parsing: Optional[bool] = True  # Control whether to parse resume contents
    evaluation_result: Optional[bool] = False  # Control whether to include evaluation report
 
class JobProfileUpdatePayload(BaseModel):
    id: int
    title: str
    jd: str = Field(..., alias="jd")

class EssentialDetails(BaseModel):
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    mobile_number: str = ""