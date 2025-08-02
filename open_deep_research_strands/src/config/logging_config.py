"""
Logging configuration for Open Deep Research Strands project.
"""
import logging
import sys
from pathlib import Path
from typing import Dict, Any

import structlog
from structlog.typing import FilteringBoundLogger


def setup_logging(
    log_level: str = "INFO", 
    log_file: str = None,
    debug_mode: bool = False
) -> FilteringBoundLogger:
    """
    Setup structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        debug_mode: Enable debug mode with detailed logging
        
    Returns:
        Configured structlog logger
    """
    # Configure standard logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s",
        stream=sys.stdout,
    )
    
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


def get_logger(name: str = None) -> FilteringBoundLogger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    if name:
        return structlog.get_logger(name)
    return structlog.get_logger("open_deep_research_strands")


class LoggerMixin:
    """
    Mixin class to add logging capabilities to any class.
    """
    
    @property
    def logger(self) -> FilteringBoundLogger:
        """Get logger instance for this class."""
        class_name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        return get_logger(class_name)
    
    def log_method_entry(self, method_name: str, **kwargs):
        """Log method entry with parameters."""
        self.logger.debug(
            f"Entering {method_name}",
            method=method_name,
            **kwargs
        )
    
    def log_method_exit(self, method_name: str, **kwargs):
        """Log method exit with results."""
        self.logger.debug(
            f"Exiting {method_name}",
            method=method_name,
            **kwargs
        )