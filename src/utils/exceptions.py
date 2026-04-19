"""Custom exceptions for the workflow automation pipeline"""


class WorkflowError(Exception):
    """Base exception for workflow automation errors"""


class ValidationError(WorkflowError):
    """Raised when data validation fails"""

    def __init__(self, message: str, errors: list = None):
        super().__init__(message)
        self.errors = errors or []


class ProcessingError(WorkflowError):
    """Raised when record processing fails"""

    def __init__(self, message: str, record_id: int = None):
        super().__init__(message)
        self.record_id = record_id


class S3ServiceError(WorkflowError):
    """Raised when S3 operations fail"""


class DatadogServiceError(WorkflowError):
    """Raised when Datadog operations fail"""


class ConfigurationError(WorkflowError):
    """Raised when configuration is invalid"""


class LLMServiceError(WorkflowError):
    """Raised when LLM API calls fail"""
