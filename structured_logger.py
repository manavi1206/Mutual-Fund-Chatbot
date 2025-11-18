"""
Structured Logger - Enterprise-grade logging with request tracking
"""
import logging
import json
import sys
from typing import Dict, Optional, Any
from datetime import datetime
import uuid


class StructuredLogger:
    """Structured logging with request ID tracking"""
    
    def __init__(self, log_level: str = "INFO", log_file: Optional[str] = None):
        """
        Initialize structured logger
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional log file path (if None, logs to stdout)
        """
        self.logger = logging.getLogger("rag_chatbot")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Remove existing handlers
        self.logger.handlers = []
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # Request ID context (thread-local storage)
        self.request_ids = {}
    
    def set_request_id(self, request_id: str):
        """Set request ID for current context"""
        import threading
        thread_id = threading.current_thread().ident
        self.request_ids[thread_id] = request_id
    
    def get_request_id(self) -> Optional[str]:
        """Get current request ID"""
        import threading
        thread_id = threading.current_thread().ident
        return self.request_ids.get(thread_id)
    
    def _format_message(self, level: str, message: str, **kwargs) -> str:
        """Format log message as JSON"""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            **kwargs
        }
        
        request_id = self.get_request_id()
        if request_id:
            log_data['request_id'] = request_id
        
        return json.dumps(log_data)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(self._format_message("DEBUG", message, **kwargs))
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(self._format_message("INFO", message, **kwargs))
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(self._format_message("WARNING", message, **kwargs))
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(self._format_message("ERROR", message, **kwargs))
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(self._format_message("CRITICAL", message, **kwargs))
    
    def log_query(self, query: str, session_id: str, response_time: float, **kwargs):
        """Log query processing"""
        self.info("query_processed",
            query=query[:100],  # Truncate long queries
            session_id=session_id,
            response_time_seconds=round(response_time, 3),
            **kwargs
        )
    
    def log_error(self, error: Exception, context: Dict[str, Any]):
        """Log error with context"""
        self.error("error_occurred",
            error_type=type(error).__name__,
            error_message=str(error),
            **context
        )
    
    def log_metric(self, metric_name: str, value: float, **kwargs):
        """Log metric"""
        self.info("metric_recorded",
            metric_name=metric_name,
            value=value,
            **kwargs
        )


# Global logger instance
_logger_instance: Optional[StructuredLogger] = None

def get_logger() -> StructuredLogger:
    """Get global logger instance"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = StructuredLogger()
    return _logger_instance

def generate_request_id() -> str:
    """Generate unique request ID"""
    return str(uuid.uuid4())

