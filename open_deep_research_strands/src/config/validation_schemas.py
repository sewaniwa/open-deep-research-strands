"""
Input validation schemas and decorators for comprehensive data validation.
"""
import functools
from typing import Dict, Any, Optional, Callable, Union, List
import json
from datetime import datetime

try:
    import jsonschema
    from jsonschema import validate, ValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    ValidationError = Exception

from ..exceptions import AgentValidationError


# Schema definitions for different components
SUPERVISOR_AGENT_SCHEMAS = {
    "conduct_research": {
        "type": "object",
        "properties": {
            "user_query": {
                "type": "string",
                "minLength": 5,
                "maxLength": 10000,
                "description": "User's research query"
            },
            "parameters": {
                "type": "object",
                "properties": {
                    "max_iterations": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "description": "Maximum research iterations"
                    },
                    "research_depth": {
                        "type": "string",
                        "enum": ["shallow", "medium", "deep"],
                        "description": "Depth of research required"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "normal", "high", "urgent"],
                        "default": "normal"
                    },
                    "timeout": {
                        "type": "number",
                        "minimum": 60,
                        "maximum": 3600,
                        "description": "Maximum execution time in seconds"
                    }
                },
                "additionalProperties": False
            }
        },
        "required": ["user_query"],
        "additionalProperties": False
    },
    "task_data": {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "minLength": 1,
                "maxLength": 100
            },
            "content": {
                "type": "object",
                "properties": {
                    "user_query": {
                        "type": "string",
                        "minLength": 5,
                        "maxLength": 10000
                    }
                },
                "required": ["user_query"]
            },
            "metadata": {
                "type": "object",
                "additionalProperties": True
            }
        },
        "required": ["task_id", "content"],
        "additionalProperties": False
    }
}

REPORT_AGENT_SCHEMAS = {
    "generate_report": {
        "type": "object",
        "properties": {
            "research_results": {
                "type": "object",
                "minProperties": 1,
                "description": "Research results to compile into report"
            },
            "research_brief": {
                "type": "object",
                "properties": {
                    "research_objective": {
                        "type": "string",
                        "minLength": 10,
                        "maxLength": 1000
                    },
                    "required_topics": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object"
                        }
                    }
                },
                "required": ["research_objective", "required_topics"]
            },
            "output_format": {
                "type": "string",
                "enum": ["markdown", "html", "json", "pdf"],
                "default": "markdown"
            },
            "quality_requirements": {
                "type": "object",
                "properties": {
                    "min_accuracy": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "min_completeness": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "min_depth": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                },
                "additionalProperties": False
            }
        },
        "required": ["research_results", "research_brief"],
        "additionalProperties": False
    }
}

ERROR_HANDLER_SCHEMAS = {
    "handle_error": {
        "type": "object", 
        "properties": {
            "error_type": {
                "type": "string",
                "enum": ["agent_failure", "task_timeout", "communication_error", 
                        "resource_exhaustion", "data_validation", "external_service", "system_error"]
            },
            "context": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "task_id": {"type": "string"},
                    "error_message": {"type": "string"},
                    "timestamp": {"type": "string"}
                },
                "required": ["agent_id", "error_message"]
            },
            "recovery_strategy": {
                "type": "string",
                "enum": ["retry", "fallback", "escalate", "ignore", "circuit_breaker"]
            }
        },
        "required": ["error_type", "context"],
        "additionalProperties": False
    }
}

# Combined schema registry
VALIDATION_SCHEMAS = {
    "supervisor_agent": SUPERVISOR_AGENT_SCHEMAS,
    "report_agent": REPORT_AGENT_SCHEMAS,
    "error_handler": ERROR_HANDLER_SCHEMAS
}


class ValidationResult:
    """Result of validation operation."""
    
    def __init__(self, is_valid: bool, errors: List[str] = None, warnings: List[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    def __bool__(self):
        return self.is_valid
    
    def add_error(self, error: str):
        """Add an error to the result."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """Add a warning to the result."""
        self.warnings.append(warning)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings
        }


class InputValidator:
    """Comprehensive input validation system."""
    
    def __init__(self):
        """Initialize validator."""
        self.schemas = VALIDATION_SCHEMAS
        self.custom_validators: Dict[str, Callable] = {}
    
    def validate_data(self, data: Any, schema_path: str) -> ValidationResult:
        """
        Validate data against specified schema.
        
        Args:
            data: Data to validate
            schema_path: Path to schema (e.g., "supervisor_agent.conduct_research")
            
        Returns:
            ValidationResult with validation status and details
        """
        result = ValidationResult(True)
        
        try:
            # Parse schema path
            parts = schema_path.split(".")
            if len(parts) != 2:
                result.add_error(f"Invalid schema path: {schema_path}")
                return result
            
            component, method = parts
            schema = self.schemas.get(component, {}).get(method)
            
            if not schema:
                result.add_error(f"Schema not found: {schema_path}")
                return result
            
            # Perform validation
            if HAS_JSONSCHEMA:
                try:
                    validate(instance=data, schema=schema)
                except ValidationError as e:
                    result.add_error(f"Validation error: {e.message}")
                    if hasattr(e, 'path') and e.path:
                        result.add_error(f"Error path: {'.'.join(str(p) for p in e.path)}")
            else:
                # Fallback validation without jsonschema
                fallback_result = self._fallback_validation(data, schema)
                if not fallback_result.is_valid:
                    result.errors.extend(fallback_result.errors)
                    result.is_valid = False
            
            # Custom validation
            custom_validator = self.custom_validators.get(schema_path)
            if custom_validator:
                try:
                    custom_result = custom_validator(data)
                    if hasattr(custom_result, 'is_valid'):
                        if not custom_result.is_valid:
                            result.errors.extend(custom_result.errors)
                            result.warnings.extend(custom_result.warnings)
                            result.is_valid = False
                except Exception as e:
                    result.add_error(f"Custom validation error: {str(e)}")
        
        except Exception as e:
            result.add_error(f"Validation system error: {str(e)}")
        
        return result
    
    def _fallback_validation(self, data: Any, schema: Dict[str, Any]) -> ValidationResult:
        """Fallback validation when jsonschema is not available."""
        result = ValidationResult(True)
        
        # Basic type checking
        if "type" in schema:
            expected_type = schema["type"]
            if expected_type == "object" and not isinstance(data, dict):
                result.add_error(f"Expected object, got {type(data).__name__}")
            elif expected_type == "string" and not isinstance(data, str):
                result.add_error(f"Expected string, got {type(data).__name__}")
            elif expected_type == "integer" and not isinstance(data, int):
                result.add_error(f"Expected integer, got {type(data).__name__}")
            elif expected_type == "number" and not isinstance(data, (int, float)):
                result.add_error(f"Expected number, got {type(data).__name__}")
            elif expected_type == "array" and not isinstance(data, list):
                result.add_error(f"Expected array, got {type(data).__name__}")
        
        # Required properties check for objects
        if isinstance(data, dict) and "required" in schema:
            for required_field in schema["required"]:
                if required_field not in data:
                    result.add_error(f"Missing required field: {required_field}")
        
        # String length validation
        if isinstance(data, str):
            if "minLength" in schema and len(data) < schema["minLength"]:
                result.add_error(f"String too short: minimum {schema['minLength']} characters")
            if "maxLength" in schema and len(data) > schema["maxLength"]:
                result.add_error(f"String too long: maximum {schema['maxLength']} characters")
        
        return result
    
    def register_custom_validator(self, schema_path: str, validator: Callable):
        """Register a custom validator for a specific schema path."""
        self.custom_validators[schema_path] = validator
    
    def get_schema(self, schema_path: str) -> Optional[Dict[str, Any]]:
        """Get schema by path."""
        parts = schema_path.split(".")
        if len(parts) == 2:
            component, method = parts
            return self.schemas.get(component, {}).get(method)
        return None


# Global validator instance
_validator = InputValidator()


def get_validator() -> InputValidator:
    """Get global validator instance."""
    return _validator


def validate_input(schema_path: str, raise_on_error: bool = True):
    """
    Decorator for input validation.
    
    Args:
        schema_path: Path to validation schema
        raise_on_error: Whether to raise exception on validation failure
        
    Returns:
        Decorated function with input validation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # For methods, first arg is usually self, second is the data to validate
            if len(args) >= 2:
                data_to_validate = args[1]
            elif kwargs:
                # Use all kwargs as data to validate
                data_to_validate = kwargs
            else:
                data_to_validate = {}
            
            validator = get_validator()
            result = validator.validate_data(data_to_validate, schema_path)
            
            if not result.is_valid:
                error_msg = f"Input validation failed for {schema_path}: {'; '.join(result.errors)}"
                if raise_on_error:
                    raise AgentValidationError(error_msg)
                else:
                    # Log warning and continue
                    print(f"Warning: {error_msg}")
            
            return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For methods, first arg is usually self, second is the data to validate
            if len(args) >= 2:
                data_to_validate = args[1]
            elif kwargs:
                # Use all kwargs as data to validate
                data_to_validate = kwargs
            else:
                data_to_validate = {}
            
            validator = get_validator()
            result = validator.validate_data(data_to_validate, schema_path)
            
            if not result.is_valid:
                error_msg = f"Input validation failed for {schema_path}: {'; '.join(result.errors)}"
                if raise_on_error:
                    raise AgentValidationError(error_msg)
                else:
                    # Log warning and continue
                    print(f"Warning: {error_msg}")
            
            return func(*args, **kwargs)
        
        # Return appropriate wrapper based on whether original function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def validate_task_data_enhanced(task_data: Any) -> ValidationResult:
    """Enhanced task data validation with detailed error reporting."""
    validator = get_validator()
    return validator.validate_data(task_data, "supervisor_agent.task_data")


def validate_research_request(data: Dict[str, Any]) -> ValidationResult:
    """Validate research request data."""
    validator = get_validator()
    return validator.validate_data(data, "supervisor_agent.conduct_research")


def validate_report_request(data: Dict[str, Any]) -> ValidationResult:
    """Validate report generation request."""
    validator = get_validator()
    return validator.validate_data(data, "report_agent.generate_report")


# Register some custom validators
def custom_query_validator(data: Dict[str, Any]) -> ValidationResult:
    """Custom validation for research queries."""
    result = ValidationResult(True)
    
    if isinstance(data, dict) and "user_query" in data:
        query = data["user_query"]
        
        # Check for potential sensitive content
        sensitive_keywords = ["password", "credit card", "ssn", "social security"]
        for keyword in sensitive_keywords:
            if keyword.lower() in query.lower():
                result.add_warning(f"Query contains potentially sensitive keyword: {keyword}")
        
        # Check for very short queries that might not be meaningful
        if len(query.strip()) < 10:
            result.add_warning("Query is very short and might not provide sufficient context")
        
        # Check for excessive special characters
        special_char_count = sum(1 for c in query if not c.isalnum() and not c.isspace())
        if special_char_count > len(query) * 0.3:
            result.add_warning("Query contains many special characters which might indicate malformed input")
    
    return result


# Register the custom validator
get_validator().register_custom_validator("supervisor_agent.conduct_research", custom_query_validator)