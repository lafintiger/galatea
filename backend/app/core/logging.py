"""Centralized logging configuration for Galatea.

Usage:
    from app.core import get_logger
    logger = get_logger(__name__)
    
    logger.debug("Detailed debug info")
    logger.info("General information")
    logger.warning("Something unexpected")
    logger.error("Something failed", exc_info=True)
"""
import logging
import sys
from typing import Optional
from datetime import datetime


# ANSI color codes for terminal output
class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


class GalateaFormatter(logging.Formatter):
    """Custom formatter with colors and structured output."""
    
    # Level -> (color, prefix)
    LEVEL_CONFIG = {
        logging.DEBUG: (Colors.DIM, "DEBUG"),
        logging.INFO: (Colors.GREEN, "INFO"),
        logging.WARNING: (Colors.YELLOW, "WARN"),
        logging.ERROR: (Colors.RED, "ERROR"),
        logging.CRITICAL: (Colors.RED + Colors.BOLD, "FATAL"),
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # Get color and prefix for this level
        color, prefix = self.LEVEL_CONFIG.get(
            record.levelno, 
            (Colors.WHITE, "LOG")
        )
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        
        # Extract module name (last part of logger name)
        module = record.name.split(".")[-1]
        if module == "__main__":
            module = "main"
        
        # Build the message
        # Format: [HH:MM:SS] [LEVEL] [module] message
        formatted = (
            f"{Colors.DIM}{timestamp}{Colors.RESET} "
            f"{color}[{prefix}]{Colors.RESET} "
            f"{Colors.CYAN}[{module}]{Colors.RESET} "
            f"{record.getMessage()}"
        )
        
        # Add exception info if present
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)
        
        return formatted


class PlainFormatter(logging.Formatter):
    """Plain formatter without colors (for file output or non-TTY)."""
    
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        module = record.name.split(".")[-1]
        
        formatted = f"{timestamp} [{record.levelname}] [{module}] {record.getMessage()}"
        
        if record.exc_info:
            formatted += "\n" + self.formatException(record.exc_info)
        
        return formatted


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
) -> None:
    """Configure logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path to write logs
    """
    # Get numeric level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Get root logger for our app
    root_logger = logging.getLogger("app")
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors (if TTY)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    if sys.stdout.isatty():
        console_handler.setFormatter(GalateaFormatter())
    else:
        console_handler.setFormatter(PlainFormatter())
    
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(PlainFormatter())
        root_logger.addHandler(file_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a module.
    
    Args:
        name: Usually __name__ from the calling module
        
    Returns:
        Configured logger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("Starting service")
    """
    # Ensure name is under our app namespace
    if not name.startswith("app"):
        name = f"app.{name}"
    
    return logging.getLogger(name)


# Initialize logging on import (can be reconfigured later)
setup_logging()

