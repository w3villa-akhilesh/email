"""
Simple Performance Evaluation Configuration Service

Hardcoded company configurations with easy customization.
Add company-specific configs directly in this file.
"""

from typing import Dict, Any
from dataclasses import dataclass, asdict

from app.utils.logger import logger


@dataclass
class PerformanceEvaluationConfig:
    """
    Company-specific performance evaluation configuration.
    
    All weights must sum to 1.0 for proper scoring calculation.
    Thresholds define performance bands for employee evaluation.
    """
    
    # Company identification
    company_id: str = "default"
    company_name: str = "Default Company"
    
    # Scoring weights (must sum to 1.0)
    attendance_weight: float = 0.15
    productivity_weight: float = 0.30
    task_quality_weight: float = 0.25
    reliability_weight: float = 0.10
    mood_weight: float = 0.10
    collaboration_weight: float = 0.10
    
    # Evaluation parameters
    work_start_time: str = "09:30"
    evaluation_period_days: int = 90
    tardiness_threshold_minutes: int = 15
    
    # Performance thresholds (0-100 scale)
    outstanding_threshold: float = 85.0
    good_threshold: float = 70.0
    satisfactory_threshold: float = 60.0
    
    # Quality score range
    max_qa_score: float = 5.0
    min_qa_score: float = 0.0
    
    # Work schedule (for attendance calculations)
    standard_work_hours: float = 8.0
    work_days_per_week: int = 5
    
    def validate_weights(self) -> bool:
        """Validate that all weights sum to 1.0 within tolerance."""
        total_weight = (
            self.attendance_weight + self.productivity_weight + 
            self.task_quality_weight + self.reliability_weight + 
            self.mood_weight + self.collaboration_weight
        )
        return abs(total_weight - 1.0) < 0.01
    
    def get_performance_band(self, score: float) -> str:
        """Get performance band classification based on score."""
        if score >= self.outstanding_threshold:
            return "Outstanding"
        elif score >= self.good_threshold:
            return "Good"
        elif score >= self.satisfactory_threshold:
            return "Satisfactory"
        else:
            return "Needs Improvement"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerformanceEvaluationConfig":
        """Create config from dictionary data."""
        return cls(**data)


# Hardcoded company configurations
COMPANY_CONFIGS = {
    # Default configuration used for all companies unless overridden
    "default": {
        "company_id": "default",
        "company_name": "Default Configuration",
        "attendance_weight": 0.15,
        "productivity_weight": 0.30,
        "task_quality_weight": 0.25,
        "reliability_weight": 0.10,
        "mood_weight": 0.10,
        "collaboration_weight": 0.10,
        "work_start_time": "09:30",
        "evaluation_period_days": 90,
        "tardiness_threshold_minutes": 15,
        "outstanding_threshold": 85.0,
        "good_threshold": 70.0,
        "satisfactory_threshold": 60.0,
        "max_qa_score": 5.0,
        "min_qa_score": 0.0,
        "standard_work_hours": 8.0,
        "work_days_per_week": 5
    },
    
    # Example company-specific configurations
    # Add more entries here as needed
    
    "example_company": {
        "company_id": "example_company",
        "company_name": "Example Technology Corp",
        "attendance_weight": 0.20,
        "productivity_weight": 0.25,
        "task_quality_weight": 0.30,
        "reliability_weight": 0.10,
        "mood_weight": 0.10,
        "collaboration_weight": 0.05,
        "work_start_time": "09:00",
        "evaluation_period_days": 90,
        "tardiness_threshold_minutes": 10,
        "outstanding_threshold": 90.0,
        "good_threshold": 75.0,
        "satisfactory_threshold": 65.0,
        "max_qa_score": 5.0,
        "min_qa_score": 0.0,
        "standard_work_hours": 8.0,
        "work_days_per_week": 5
    },
    
    "startup_company": {
        "company_id": "startup_company",
        "company_name": "StartupTech Solutions",
        "attendance_weight": 0.10,
        "productivity_weight": 0.35,
        "task_quality_weight": 0.30,
        "reliability_weight": 0.05,
        "mood_weight": 0.15,
        "collaboration_weight": 0.05,
        "work_start_time": "10:00",
        "evaluation_period_days": 60,
        "tardiness_threshold_minutes": 20,
        "outstanding_threshold": 80.0,
        "good_threshold": 65.0,
        "satisfactory_threshold": 50.0,
        "max_qa_score": 5.0,
        "min_qa_score": 0.0,
        "standard_work_hours": 9.0,
        "work_days_per_week": 5
    }
}


class PerformanceConfigService:
    """
    Simple service for company-specific performance evaluation configurations.
    
    Uses hardcoded configurations with company-specific overrides.
    """
    
    def __init__(self):
        """Initialize the configuration service."""
        self._config_cache: Dict[str, PerformanceEvaluationConfig] = {}
        logger.info("Performance configuration service initialized with hardcoded configs")
    
    def get_config(self, company_id: str) -> PerformanceEvaluationConfig:
        """
        Get performance evaluation configuration for a company.
        
        Simple mapping:
        1. Check if company has specific config in COMPANY_CONFIGS
        2. If not found, use default config
        3. Update company info and return
        
        Args:
            company_id: Company identifier
            
        Returns:
            PerformanceEvaluationConfig: Company-specific or default configuration
        """
        # Check cache first
        if company_id in self._config_cache:
            logger.debug(f"Retrieved cached config for company: {company_id}")
            return self._config_cache[company_id]
        
        # Check if company has specific configuration
        if company_id in COMPANY_CONFIGS:
            config_data = COMPANY_CONFIGS[company_id].copy()
            logger.info(f"Using company-specific config for {company_id}")
        else:
            # Use default configuration
            config_data = COMPANY_CONFIGS["default"].copy()
            config_data["company_id"] = company_id
            config_data["company_name"] = f"Company {company_id}"
            logger.info(f"Using default config for company {company_id}")
        
        # Create configuration object
        config = PerformanceEvaluationConfig.from_dict(config_data)
        
        # Validate configuration
        if not config.validate_weights():
            logger.error(f"Invalid weights in config for company {company_id}, weights must sum to 1.0")
            # Fall back to default
            config = PerformanceEvaluationConfig()
            config.company_id = company_id
            config.company_name = f"Company {company_id}"
        
        # Cache the configuration
        self._config_cache[company_id] = config
        
        return config
    
    def clear_cache(self, company_id: str = None) -> None:
        """
        Clear configuration cache.
        
        Args:
            company_id: Specific company to clear, or None to clear all
        """
        if company_id:
            self._config_cache.pop(company_id, None)
            logger.debug(f"Cleared config cache for company: {company_id}")
        else:
            self._config_cache.clear()
            logger.debug("Cleared all config cache")
    
    def list_configured_companies(self) -> list[str]:
        """
        List all companies that have specific configurations.
        
        Returns:
            List of company IDs with custom configurations (excludes 'default')
        """
        company_ids = [company_id for company_id in COMPANY_CONFIGS.keys() if company_id != "default"]
        logger.debug(f"Found company-specific configurations: {company_ids}")
        return company_ids


# Global service instance
_config_service = None


def get_performance_config_service() -> PerformanceConfigService:
    """
    Get the global performance configuration service instance.
    
    Returns:
        PerformanceConfigService: Singleton service instance
    """
    global _config_service
    if _config_service is None:
        _config_service = PerformanceConfigService()
    return _config_service


def get_performance_config(company_id: str) -> PerformanceEvaluationConfig:
    """
    Convenience function to get performance evaluation configuration for a company.
    
    Args:
        company_id: Company identifier
        
    Returns:
        PerformanceEvaluationConfig: Company-specific or default configuration
    """
    service = get_performance_config_service()
    return service.get_config(company_id)


# Export classes and functions
__all__ = [
    "PerformanceEvaluationConfig",
    "PerformanceConfigService", 
    "get_performance_config_service",
    "get_performance_config",
    "COMPANY_CONFIGS"
]