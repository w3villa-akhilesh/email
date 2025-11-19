# Performance Evaluation Configuration Service

## Overview

Simple performance evaluation configuration service with hardcoded company configurations. Add company-specific configs directly in the Python file for easy management.

## Features

### Hardcoded Configuration Management
- **Company-Specific Configs**: Add entries to `COMPANY_CONFIGS` dictionary
- **Default Configuration**: Used when no company-specific config exists
- **Easy Management**: Edit configurations directly in Python code
- **Configuration Validation**: Ensures weights sum to 1.0 and thresholds are valid

### Configuration Loading
**Simple Priority**:
1. **Company-Specific Config**: Entry in `COMPANY_CONFIGS` dictionary (if exists)
2. **Default Config**: Uses "default" entry from `COMPANY_CONFIGS` 
3. **Fallback**: Hardcoded defaults in class (last resort)

**Current Approach**: All companies use the default configuration unless you add a specific entry to `COMPANY_CONFIGS`.

### Integration with Performance Evaluation Agents
- **Template Variable Injection**: Configuration values are automatically injected into agent prompts
- **Session State Management**: Config is stored in ADK session state for agent access
- **Dynamic Prompt Values**: Agents receive actual company values instead of generic "configurable" text

## Configuration Schema

```python
# In app/services/performance_config_service.py
COMPANY_CONFIGS = {
    "company_id": {
        "company_id": "unique_company_identifier",
        "company_name": "Human Readable Company Name",
        
        # Scoring weights (must sum to 1.0)
        "attendance_weight": 0.15,
        "productivity_weight": 0.30, 
        "task_quality_weight": 0.25,
        "reliability_weight": 0.10,
        "mood_weight": 0.10,
        "collaboration_weight": 0.10,
        
        # Evaluation parameters
        "work_start_time": "09:30",
        "evaluation_period_days": 90,
        "tardiness_threshold_minutes": 15,
        
        # Performance thresholds (0-100 scale)
        "outstanding_threshold": 85.0,
        "good_threshold": 70.0,
        "satisfactory_threshold": 60.0,
        
        # Quality score range
        "max_qa_score": 5.0,
        "min_qa_score": 0.0,
        
        # Work schedule
        "standard_work_hours": 8.0,
        "work_days_per_week": 5
    }
}
```

## Usage Examples

### Basic Usage
```python
from app.services.performance_config_service import get_performance_config

# Get config for any company (uses default config unless company-specific entry exists)
config = get_performance_config("company_123")
print(f"Attendance weight: {config.attendance_weight}")  # From COMPANY_CONFIGS["default"]
print(f"Work start time: {config.work_start_time}")      # From COMPANY_CONFIGS["default"]
print(f"Outstanding threshold: {config.outstanding_threshold}")  # From COMPANY_CONFIGS["default"]
```

### Adding Company-Specific Configurations
To add a company-specific configuration, edit the `COMPANY_CONFIGS` dictionary in `app/services/performance_config_service.py`:

```python
# In app/services/performance_config_service.py
COMPANY_CONFIGS = {
    "default": {
        # ... default configuration
    },
    
    # Add new company configuration here
    "tech_startup": {
        "company_id": "tech_startup",
        "company_name": "Tech Startup Inc",
        "attendance_weight": 0.10,      # Less emphasis on attendance
        "productivity_weight": 0.35,    # High emphasis on productivity  
        "task_quality_weight": 0.30,
        "mood_weight": 0.15,            # High emphasis on wellbeing
        "work_start_time": "10:00",     # Flexible start time
        "tardiness_threshold_minutes": 20,
        "outstanding_threshold": 80.0,   # Lower bar for recognition
        "good_threshold": 65.0,
        "satisfactory_threshold": 50.0,
        "max_qa_score": 5.0,
        "min_qa_score": 0.0,
        "standard_work_hours": 9.0,
        "work_days_per_week": 5
    }
}
```

**Note**: Most companies will use the default configuration. Only add company-specific entries when different evaluation criteria are needed.

## Agent Integration

### How Configuration Reaches Agents

1. **Performance Pipeline Execution**:
   ```python
   # In run_performance_evaluation_pipeline()
   config = get_performance_config(company_id)
   session.state["evaluation_config"] = config.to_dict()
   ```

2. **Template Variable Injection**:
   ```text
   // In agent prompts:
   On-time percentage (check-in before {evaluation_config[work_start_time]})
   Outstanding: ≥{evaluation_config[outstanding_threshold]} points
   ```

3. **Dynamic Prompt Values**:
   - ❌ Before: "Outstanding: ≥85 points (configurable)"
   - ✅ After: "Outstanding: ≥90 points" (actual company threshold)

### Agent Prompt Examples

**Metrics Calculation Agent**:
```text
1. **Attendance Discipline**
   - On-time percentage (check-in before {evaluation_config[work_start_time]})
   - Tardiness count (late arrivals >{evaluation_config[tardiness_threshold_minutes]} min)
```

**Scoring Agent**:
```text
Scoring Weights:
- Attendance discipline: {evaluation_config[attendance_weight]:.0%}
- Productivity efficiency: {evaluation_config[productivity_weight]:.0%}
- Task quality: {evaluation_config[task_quality_weight]:.0%}

Performance Bands:
- Outstanding: ≥{evaluation_config[outstanding_threshold]} points
- Good: ≥{evaluation_config[good_threshold]} points
```

## Configuration Files

### Default Configuration

**Primary Config** (`default.json`):
- Used by all companies unless overridden
- Standard evaluation criteria and thresholds
- Balanced scoring weights
- Can be modified to change defaults for all companies

### Optional Company-Specific Configurations

**Traditional Enterprise** (`example_company.json`) - *Optional override example*:
- Higher attendance weight (20%)
- Standard work hours (9:00 AM start)  
- Higher performance thresholds

**Tech Startup** (`startup_company.json`) - *Optional override example*:
- Lower attendance weight (10%)
- Flexible start time (10:00 AM)
- Higher productivity weight (35%)
- Emphasis on wellbeing (15%)

## Service Architecture

### PerformanceConfigService Class
- **Simple File Loading**: Map company ID to JSON file
- **Caching**: In-memory caching for performance  
- **Validation**: Ensures config integrity
- **File Management**: Save/load configurations

### Key Methods
```python
get_config(company_id: str) -> PerformanceEvaluationConfig  # Main method
clear_cache(company_id: str = None) -> None  # Clear cache
list_configured_companies() -> List[str]  # List companies with custom configs
```

## ADK Compliance

This configuration service follows ADK best practices:

- ✅ **Session State Integration**: Configs stored in ADK session state
- ✅ **Template Variable Support**: Direct integration with ADK template engine
- ✅ **Environment Variable Support**: Standard ADK configuration patterns
- ✅ **Caching Strategy**: Performance optimization following ADK guidelines
- ✅ **Error Handling**: Graceful fallbacks and proper error responses
- ✅ **Logging**: Comprehensive logging using ADK logging patterns

## Future Enhancements

### Database Integration
```python
# Future database loading support
def _load_from_database(self, company_id: str) -> Optional[PerformanceEvaluationConfig]:
    # Load from company_performance_configs table
    pass
```

### Advanced Features
- **Configuration Versioning**: Track config changes over time
- **A/B Testing**: Support multiple config versions per company
- **Role-Based Configs**: Different configs for different employee roles
- **Dynamic Adjustments**: Real-time config updates during evaluation

## File Structure

```
app/
├── services/
│   └── performance_config_service.py     # Main service with COMPANY_CONFIGS dictionary
└── helpers/
    └── performance_evaluation_agent.py   # Uses config service
```

## Troubleshooting

### Common Issues

1. **Weights Don't Sum to 1.0**
   ```
   ERROR: Invalid configuration: weights must sum to 1.0
   ```
   **Solution**: Check `default.json` or company-specific file - ensure all weight values sum to exactly 1.0

2. **All Companies Using Same Config**
   ```
   INFO: Using default config file for company XYZ
   ```
   **Expected Behavior**: All companies use `default.json` unless you create company-specific files

3. **Invalid JSON Configuration**
   ```
   ERROR: Error loading default config file: Invalid JSON
   ```
   **Solution**: Validate JSON syntax in `default.json` file

### Debugging
```python
# Check what config is being used
config = get_performance_config("your_company_id")
print(f"Using config: {config.to_dict()}")

# List available configurations
service = get_performance_config_service()
companies = service.list_configured_companies()
print(f"Configured companies: {companies}")
```

---

**Created**: Company-specific performance evaluation configuration system  
**ADK Compatible**: ✅ Full ADK integration and best practices  
**Flexibility**: ✅ Multi-source configuration with intelligent fallbacks