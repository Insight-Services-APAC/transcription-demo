import logging
import functools
import traceback
import time
from datetime import datetime
from app.errors.exceptions import ServiceError
from app.errors.logger import log_exception

logger = logging.getLogger("app.services")


def retry_on_error(max_retries=3, retry_delay=1, exceptions=(Exception,), logger=None):
    """
    Decorator to retry a function on specific exceptions.

    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds (doubles with each retry)
        exceptions: Tuple of exceptions to catch and retry on
        logger: Logger to use (defaults to app.services)

    Returns:
        Decorator function
    """
    if logger is None:
        logger = logging.getLogger("app.services")

    def decorator(func):

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            retry_count = 0
            delay = retry_delay
            while retry_count < max_retries:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retry_count += 1
                    last_exception = e
                    if retry_count < max_retries:
                        logger.warning(
                            f"Retry {retry_count}/{max_retries} for {func.__name__} due to: {str(e)}"
                        )
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.error(
                            f"Failed after {max_retries} retries: {func.__name__}"
                        )
                        break
            if last_exception:
                if isinstance(last_exception, ServiceError):
                    raise last_exception
                else:
                    raise ServiceError(
                        f"Service operation failed after {max_retries} retries: {str(last_exception)}",
                        operation=func.__name__,
                    ) from last_exception

        return wrapper

    return decorator


def log_service_call(service_name):
    """
    Decorator to log service calls with timing information.

    Args:
        service_name: Name of the service being called

    Returns:
        Decorator function
    """

    def decorator(func):

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            operation = func.__name__
            logger.info(f"Service call started: {service_name}.{operation}")
            try:
                result = func(*args, **kwargs)
                elapsed_time = time.time() - start_time
                logger.info(
                    f"Service call completed: {service_name}.{operation} in {elapsed_time:.2f}s"
                )
                return result
            except Exception as e:
                elapsed_time = time.time() - start_time
                log_exception(
                    e,
                    logger=logger,
                    extra={
                        "service": service_name,
                        "operation": operation,
                        "elapsed_time": elapsed_time,
                    },
                )
                raise

        return wrapper

    return decorator


class ServiceBase:
    """Base class for service implementations with error handling."""

    def __init__(self, service_name=None):
        """
        Initialize the service base.

        Args:
            service_name: Name of the service for logging
        """
        self.service_name = service_name or self.__class__.__name__
        self.logger = logging.getLogger(f"app.services.{self.service_name.lower()}")

    def _handle_service_error(self, operation, exception, **context):
        """
        Handle a service error by logging and wrapping in a ServiceError.

        Args:
            operation: Name of the operation that failed
            exception: The exception that was raised
            context: Additional context information

        Returns:
            A ServiceError instance
        """
        log_exception(
            exception, logger=self.logger, extra={"operation": operation, **context}
        )
        if isinstance(exception, ServiceError):
            return exception
        return ServiceError(
            f"{self.service_name} error in {operation}: {str(exception)}",
            service=self.service_name,
            operation=operation,
            **context,
        )
