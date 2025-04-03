class AppError(Exception):
    """Base exception class for application errors."""

    status_code = 500
    error_code = "app_error"

    def __init__(self, message=None, status_code=None, payload=None):
        super().__init__(message)
        self.message = message or "An unexpected error occurred"
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload or {}

    def to_dict(self):
        """Convert exception to dictionary for JSON response."""
        error_dict = {
            "status": "error",
            "error": {"code": self.error_code, "message": self.message},
        }
        if self.payload:
            error_dict["error"].update(self.payload)
        return error_dict


class ValidationError(AppError):
    """Exception raised for validation errors."""

    status_code = 400
    error_code = "validation_error"

    def __init__(self, message="Invalid input data", field=None, **kwargs):
        payload = kwargs
        if field:
            payload["field"] = field
        super().__init__(message, payload=payload)


class ResourceNotFoundError(AppError):
    """Exception raised when a requested resource is not found."""

    status_code = 404
    error_code = "not_found"


class AuthorizationError(AppError):
    """Exception raised for authorization errors."""

    status_code = 403
    error_code = "forbidden"


class AuthenticationError(AppError):
    """Exception raised for authentication errors."""

    status_code = 401
    error_code = "unauthorized"


class ServiceError(AppError):
    """Exception raised for errors in external services."""

    error_code = "service_error"

    def __init__(self, message="External service error", service=None, **kwargs):
        payload = kwargs
        if service:
            payload["service"] = service
        super().__init__(message, payload=payload)


class StorageError(ServiceError):
    """Exception raised for storage-related errors."""

    error_code = "storage_error"


class TranscriptionError(ServiceError):
    """Exception raised for transcription service errors."""

    error_code = "transcription_error"


class DatabaseError(AppError):
    """Exception raised for database errors."""

    error_code = "database_error"


class UploadError(AppError):
    """Exception raised for file upload errors."""

    status_code = 400
    error_code = "upload_error"

    def __init__(self, message="File upload error", filename=None, **kwargs):
        payload = kwargs
        if filename:
            payload["filename"] = filename
        super().__init__(message, payload=payload)
