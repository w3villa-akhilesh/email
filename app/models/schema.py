from pydantic import BaseModel, Field, field_validator, model_validator
from app.utils.logger import logger
from typing import Dict, List, Optional, Literal, Any, Union
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

class PMBoardAgentPayload(BaseModel):
    company_id: Union[str, int]  # Accept both string and integer
    user_id: Union[str, int]  # Accept both string and integer
    origin: str
    project_id: int
    data: dict  

    @model_validator(mode="before")
    @classmethod
    def _log_raw_payload(cls, value):
        # Log the incoming payload before validation to aid debugging 422s
        try:
            logger.info(f"[PMBoardAgentPayload] Raw payload received: {value}")
        except Exception:
            # Avoid breaking validation flow if logging fails
            pass
        return value

class HRMSRequest(BaseModel):
    query: str
    number: str

class CoordinatorAgentRequest(BaseModel):
    query: str  # Query to be processed by the Coordinator Agent
    query_id: str
    origin: Optional[str] = None
    parent_origin: Optional[str] = None
    mode: Optional[str] = None
    preloaded_context:str = None
    # Optional multimodal input support
    input_mode: Optional[str] = None  # e.g., "text" | "voice_note" | "image"
    # Accepts a single S3 URL or a list of S3 URLs (for multiple images)
    input_data_url: Optional[Union[str, List[str]]] = None
    
    
class InvokeAgentRequest(BaseModel):
    query: str  # Query to be processed by the IATS Agent
    user_id: str
    origin: Optional[str] = None
    session_id: str
    image_url: Optional[str] = None  # Optional image URL for vision analysis
    extracted_info_from_image: Optional[str] = None  # Optional extracted information from image
    app_name: str

class instruction_validation_result(BaseModel):
    type: Literal["instruction", "warning", "error"]
    text: Optional[str] = None
    message: Optional[str] = None
    match: Optional[str] = None
    recipients: List[Literal["ADMIN", "USER", "PROJECT_MANAGER", "TESTER", "CLIENT"]]

class result_with_reasoning(BaseModel):
    result: instruction_validation_result
    reasoning: str

class instruction_validation_response(BaseModel):
    instructions_list: Optional[List[str]] = None  # Allow None or empty list
    user_instruction: str
    team_members: List[str]
    company_id: Union[str, int]
    origin: str

    @model_validator(mode="before")
    @classmethod
    def _log_raw_payload(cls, value):
        # Log the incoming payload before validation to aid debugging 422s
        try:
            logger.info(f"[instruction_validation_response] Raw payload received: {value}")
        except Exception:
            # Avoid breaking validation flow if logging fails
            pass
        return value

class MatchingCriteria(BaseModel):
    min_total_experience: Optional[int] = Field(default=None, description="Minimum years of experience (e.g. 3)")
    required_skills: Optional[List[str]] = Field(default=None, description='Required technical skills (e.g. ["Java", "Spring", "SQL"])')
    accepted_locations: Optional[List[str]] = Field(default=None, description='Acceptable work locations (e.g. ["Remote", "India", "USA"])')
    max_notice_period: Optional[int] = Field(default=None, description="Maximum notice period in days (e.g. 60)")
    min_education_level: Optional[str] = Field(default=None, description='Minimum education level (e.g. "Bachelor\'s")')
    work_authorization: Optional[str] = Field(default=None, description="Work authorization requirements")
    custom_requirements: Optional[str] = Field(default=None, description="Any additional custom requirements")

class ScoringCriteria(BaseModel):
    skill_match_points: Optional[dict] = Field(default=None, description='Points for matching required skills (e.g. {"3_skills": 10, "4_skills": 20, "5_plus_skills": 30})')
    experience_points: Optional[dict] = Field(default=None, description='Points for experience brackets (e.g. {"3_5_years": 10, "5_7_years": 15, "7_plus_years": 20})')
    education_points: Optional[dict] = Field(default=None, description='Points for education levels and certifications (e.g. {"bachelors": 5, "masters": 10, "relevant_cert": 5})')
    location_notice_points: Optional[dict] = Field(default=None, description='Points for location and notice period (e.g. {"preferred_location": 5, "short_notice": 5})')
    communication_points: Optional[dict] = Field(default=None, description='Points for communication skills and resume quality (e.g. {"language_fluency": 5, "resume_quality": 5})')
    role_similarity_points: Optional[dict] = Field(default=None, description='Points for role alignment (e.g. {"high_match": 15, "medium_match": 10, "low_match": 5})')
    custom_scoring: Optional[str] = Field(default=None, description="Any additional custom scoring criteria")

# Define schema for extra info like skills etc 
class Extra_info(BaseModel):
    name: str
    value: str
    description: Optional[str] = None

# Define schema for cards 
class Cards(BaseModel):
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    extra_infos: Optional[List[Extra_info]] = None
    links: Optional[List[str]] = None

# Define schema for table
class Table(BaseModel):
    columns: List[str]
    rows: List[List[str]]

# Define schema for the full response
class IATSResponse(BaseModel):
    status: str
    response_type: Literal["card", "text", "table", "mixed"]
    summary: Optional[str] = None
    cards: Optional[List[Cards]] = None
    table: Optional[Table] = None
    suggestions: Optional[List[str]] = None
    full_response: str
    event_id: Optional[str] = None

# Define schema for the full response
class TriageResponse(BaseModel):
    status: str
    type: str
    message: str
    query: str
    action: str
    response: Dict
    session_id: str

class rename_chatname_payload(BaseModel):
    session_id: str
    chat_name: str

class DeleteSessionRequest(BaseModel):
    origin: Optional[str] = None

class MatchingCompletionNotificationPayload(BaseModel):
    custom_matching_id: str
    session_id: str
    status: str
    message: Optional[str] = None
    origin: str

# Request body model
class CandidateSequentialMatchingRequest(BaseModel):
    instructions: Dict
    company_id: str
    origin: str

# Output model
class SequentialCompletionOutput(BaseModel):
    job_applicant_id: str
    job_matching_percentage: float
    job_matching_percentage_reason: str

# ============================================================================
# Employee Performance Evaluation Schemas
# ============================================================================

class AttendanceRecord(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    check_in: str = Field(..., description="Check-in time in HH:MM format")
    check_out: str = Field(..., description="Check-out time in HH:MM format")

class MoodEntry(BaseModel):
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    mood: str = Field(..., description="Mood category (happy, neutral, stressed, motivated, frustrated, satisfied, etc.)")
    notes: Optional[str] = Field(default="", description="Additional notes about the mood entry")

class LeaveRecord(BaseModel):
    type: str = Field(..., description="Leave type (annual, sick, personal, etc.)")
    start: str = Field(..., description="Leave start date in YYYY-MM-DD format")
    end: str = Field(..., description="Leave end date in YYYY-MM-DD format")
    status: str = Field(..., description="Leave status (approved, pending, rejected)")

class WorkLogEntry(BaseModel):
    task_id: str = Field(..., description="Unique task identifier")
    project: str = Field(..., description="Project identifier or name")
    start: str = Field(..., description="Work start time in YYYY-MM-DD HH:MM format")
    end: str = Field(..., description="Work end time in YYYY-MM-DD HH:MM format")
    
    @field_validator("task_id", mode="before")
    @classmethod
    def _coerce_task_id(cls, v):
        return None if v is None else str(v)

class TaskRecord(BaseModel):
    task_id: str = Field(..., description="Unique task identifier")
    name: str = Field(..., description="Task name or description")
    estimated_hours: float = Field(..., description="Originally estimated hours for the task")
    actual_hours: float = Field(..., description="Actual hours spent on the task")
    status: str = Field(..., description="Task status (done, in_progress, cancelled, etc.)")
    qa_score: float = Field(..., description="Quality assurance score (0.0 to 5.0)")
    reopen_count: int = Field(default=0, description="Number of times the task was reopened")
    
    @field_validator("task_id", mode="before")
    @classmethod
    def _coerce_task_id(cls, v):
        return None if v is None else str(v)

class EvaluationPeriod(BaseModel):
    start_date: str = Field(..., description="Evaluation period start date in YYYY-MM-DD format")
    end_date: str = Field(..., description="Evaluation period end date in YYYY-MM-DD format")

class EmployeePerformanceData(BaseModel):
    """
    Comprehensive employee performance data schema for evaluation.
    All fields are validated for correct formats and types.
    """
    employee_id: str = Field(..., description="Unique employee identifier")
    employee_name: str = Field(..., description="Employee full name")
    evaluation_period: EvaluationPeriod = Field(..., description="Period being evaluated")
    
    # Performance data arrays (all optional but validated when present)
    attendance: List[AttendanceRecord] = Field(default=[], description="Daily attendance records")
    mood: List[MoodEntry] = Field(default=[], description="Mood and wellbeing entries")
    leave: List[LeaveRecord] = Field(default=[], description="Leave records")
    work_logs: List[WorkLogEntry] = Field(default=[], description="Time-tracked work activities")
    tasks: List[TaskRecord] = Field(default=[], description="Task completion records")

class PerformanceEvaluationRequest(BaseModel):
    """Request schema for performance evaluation with employee data."""
    employee_data: EmployeePerformanceData = Field(..., description="Employee performance data")
    evaluation_options: Optional[Dict] = Field(default={}, description="Additional evaluation options")

class AttendanceDisciplineMetrics(BaseModel):
    """Attendance discipline metrics with specific validation."""
    on_time_percentage: float = Field(..., ge=0, le=100, description="Percentage of on-time arrivals")
    average_daily_hours_worked: float = Field(..., ge=0, le=24, description="Average hours worked per day")
    tardiness_count: int = Field(..., ge=0, description="Number of late arrivals")
    consistency_score: float = Field(..., ge=0, le=100, description="Score based on consistency of work hours")

class ProductivityEfficiencyMetrics(BaseModel):
    """Productivity and efficiency metrics with validation."""
    task_completion_ratio: float = Field(..., ge=0, le=200, description="Ratio of estimated to actual hours")
    time_variance_percentage: float = Field(..., ge=0, le=100, description="Percentage variance in time estimates")
    project_efficiency: Dict[str, float] = Field(..., description="Efficiency scores by project")

class TaskQualityMetrics(BaseModel):
    """Task quality metrics with validation."""
    average_qa_score: float = Field(..., ge=0, le=100, description="Average QA score normalized to 100")
    reopen_rate: float = Field(..., ge=0, le=100, description="Percentage of tasks reopened")
    quality_consistency_trend: float = Field(..., ge=0, le=100, description="Trend in quality consistency")

class ReliabilityMetrics(BaseModel):
    """Reliability metrics with validation."""
    unplanned_absence_percentage: float = Field(..., ge=0, le=100, description="Percentage of unplanned absences")
    leave_frequency_pattern: str = Field(..., description="Pattern of leave frequency (low/normal/high)")
    advance_notice_compliance: float = Field(..., ge=0, le=100, description="Percentage of leaves with proper notice")

class MoodWellbeingMetrics(BaseModel):
    """Mood and wellbeing metrics with validation."""
    positive_mood_percentage: float = Field(..., ge=0, le=100, description="Percentage of positive moods")
    negative_mood_streaks: int = Field(..., ge=0, description="Maximum consecutive negative mood days")
    mood_stability_index: float = Field(..., ge=0, le=100, description="Index of mood stability")

class RepetitionIndexMetrics(BaseModel):
    """Repetition analysis metrics with validation."""
    tasks_appearing_three_times: List[str] = Field(default=[], description="Tasks appearing 3+ times")
    repetitive_work_patterns: float = Field(..., ge=0, le=100, description="Percentage of repetitive work")

class MetricsCalculationMetadata(BaseModel):
    """Metadata about the metrics calculation."""
    data_quality_score: float = Field(..., ge=0, le=100, description="Overall data quality score")
    confidence_level: float = Field(..., ge=0, le=100, description="Confidence in calculations")
    missing_data_flags: List[str] = Field(default=[], description="Flags for missing/incomplete data")

class PerformanceMetrics(BaseModel):
    """Schema for computed performance metrics with strict validation."""
    attendance_discipline: AttendanceDisciplineMetrics = Field(..., description="Attendance-related metrics")
    productivity_efficiency: ProductivityEfficiencyMetrics = Field(..., description="Productivity and efficiency metrics")
    task_quality: TaskQualityMetrics = Field(..., description="Task quality metrics")
    reliability: ReliabilityMetrics = Field(..., description="Leave and reliability metrics")
    mood_wellbeing: MoodWellbeingMetrics = Field(..., description="Mood and wellbeing metrics")
    repetition_index: RepetitionIndexMetrics = Field(..., description="Repetitive task analysis")
    calculation_metadata: MetricsCalculationMetadata = Field(..., description="Calculation quality metadata")

class WeightedBreakdown(BaseModel):
    """Weighted scores for each performance dimension."""
    attendance_weighted: float = Field(..., ge=0, le=100, description="Weighted attendance score")
    productivity_weighted: float = Field(..., ge=0, le=100, description="Weighted productivity score")
    task_quality_weighted: float = Field(..., ge=0, le=100, description="Weighted task quality score")
    reliability_weighted: float = Field(..., ge=0, le=100, description="Weighted reliability score")
    mood_weighted: float = Field(..., ge=0, le=100, description="Weighted mood score")
    repetition_weighted: float = Field(..., ge=0, le=100, description="Weighted repetition score")

class PerformanceScores(BaseModel):
    """Schema for weighted performance scores with strict validation."""
    attendance_score: float = Field(..., ge=0, le=100, description="Attendance discipline score")
    productivity_score: float = Field(..., ge=0, le=100, description="Productivity efficiency score")
    task_quality_score: float = Field(..., ge=0, le=100, description="Task quality score")
    reliability_score: float = Field(..., ge=0, le=100, description="Reliability score")
    mood_wellbeing_score: float = Field(..., ge=0, le=100, description="Mood and wellbeing score")
    repetition_index_score: float = Field(..., ge=0, le=100, description="Repetition index score")
    overall_score: float = Field(..., ge=0, le=100, description="Overall performance score")
    performance_band: str = Field(..., description="Performance classification")
    weighted_breakdown: WeightedBreakdown = Field(..., description="Detailed weighted scores")
    confidence_level: float = Field(..., ge=0, le=100, description="Confidence in scoring (0-100)")
    data_quality_notes: List[str] = Field(default=[], description="Notes about data quality")

class InsightsAndTrends(BaseModel):
    """Schema for performance insights and automation recommendations."""
    key_findings: List[str] = Field(..., description="Key performance insights")
    trend_analysis: Dict[str, Any] = Field(..., description="Trend analysis results")
    repetitive_tasks: List[Dict[str, Any]] = Field(..., description="Repetitive tasks with automation potential")
    automation_recommendations: List[Dict[str, Any]] = Field(..., description="Specific automation suggestions")
    performance_insights: Dict[str, List[str]] = Field(..., description="Categorized insights (strengths/risks/opportunities)")
    behavioral_patterns: List[str] = Field(..., description="Observed behavioral patterns")
