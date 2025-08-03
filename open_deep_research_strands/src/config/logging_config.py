"""
Logging configuration for Open Deep Research Strands project.
"""
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Union

# Try to import structlog, fall back to standard logging if not available
try:
    import structlog
    from structlog.typing import FilteringBoundLogger
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False
    FilteringBoundLogger = logging.Logger


def setup_logging(
    log_level: str = "INFO", 
    log_file: str = None,
    debug_mode: bool = False
) -> Union[FilteringBoundLogger, logging.Logger]:
    """
    Setup structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        debug_mode: Enable debug mode with detailed logging
        
    Returns:
        Configured logger (structlog if available, otherwise standard logging)
    """
    # Configure standard logging
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    if debug_mode:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        stream=sys.stdout,
    )
    
    if not HAS_STRUCTLOG:
        # Fall back to standard logging
        logger = logging.getLogger("open_deep_research_strands")
        logger.info(
            f"Logging configured (standard logging) - log_level={log_level}, debug_mode={debug_mode}"
        )
        return logger
    
    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    if debug_mode:
        processors.extend([
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
        ])
    
    # Add console formatting
    processors.append(
        structlog.dev.ConsoleRenderer(colors=True)
    )
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Create application logger
    logger = structlog.get_logger("open_deep_research_strands")
    
    # Log configuration details
    logger.info(
        "Logging configured",
        log_level=log_level,
        debug_mode=debug_mode,
        log_file=log_file,
    )
    
    return logger


def get_logger(name: str = None) -> Union[FilteringBoundLogger, logging.Logger]:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    if not HAS_STRUCTLOG:
        # Fall back to standard logging
        return logging.getLogger(name or "open_deep_research_strands")
    
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger("open_deep_research_strands")


class LoggerMixin:
    """
    Mixin class to add logging capabilities to any class.
    """
    
    @property
    def logger(self) -> Union[FilteringBoundLogger, logging.Logger]:
        """Get logger instance for this class."""
        class_name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        return get_logger(class_name)
    
    def log_method_entry(self, method_name: str, **kwargs):
        """Log method entry with parameters."""
        if HAS_STRUCTLOG:
            self.logger.debug(
                f"Entering {method_name}",
                method=method_name,
                **kwargs
            )
        else:
            self.logger.debug(f"Entering {method_name} - {kwargs}")
    
    def log_method_exit(self, method_name: str, **kwargs):
        """Log method exit with results."""
        if HAS_STRUCTLOG:
            self.logger.debug(
                f"Exiting {method_name}",
                method=method_name,
                **kwargs
            )
        else:
            self.logger.debug(f"Exiting {method_name} - {kwargs}")