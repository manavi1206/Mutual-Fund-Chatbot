"""
Enhanced Error Handler - Comprehensive error handling with retry and categorization
Enterprise-grade error management
"""
from typing import Dict, Optional, Callable, Any, Tuple
import time
from enum import Enum
import traceback


class ErrorCategory(Enum):
    """Error categories"""
    USER_ERROR = "user_error"  # User input issues (can retry with different input)
    RETRYABLE = "retryable"  # Transient errors (network, timeout)
    SYSTEM_ERROR = "system_error"  # System issues (needs attention)
    AUTH_ERROR = "auth_error"  # Authentication/authorization issues
    RATE_LIMIT = "rate_limit"  # Rate limiting (should wait)
    NOT_FOUND = "not_found"  # Resource not found


class EnhancedErrorHandler:
    """Enhanced error handling with categorization and retry logic"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize error handler
        
        Args:
            max_retries: Maximum retry attempts
            retry_delay: Initial retry delay in seconds
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.error_counts = {}  # Track error frequencies
    
    def categorize_error(self, error: Exception) -> ErrorCategory:
        """
        Categorize error type
        
        Args:
            error: Exception to categorize
            
        Returns:
            Error category
        """
        error_type = type(error).__name__
        error_message = str(error).lower()
        
        # Network/timeout errors - retryable
        if any(keyword in error_message for keyword in ['timeout', 'connection', 'network', 'unavailable']):
            return ErrorCategory.RETRYABLE
        
        # Rate limiting
        if any(keyword in error_message for keyword in ['rate limit', '429', 'too many requests']):
            return ErrorCategory.RATE_LIMIT
        
        # Authentication errors
        if any(keyword in error_message for keyword in ['auth', 'unauthorized', 'forbidden', '401', '403']):
            return ErrorCategory.AUTH_ERROR
        
        # Not found
        if any(keyword in error_message for keyword in ['not found', '404', 'missing']):
            return ErrorCategory.NOT_FOUND
        
        # User input errors (ValueError, KeyError for user data)
        if isinstance(error, (ValueError, KeyError)) and 'user' in error_message:
            return ErrorCategory.USER_ERROR
        
        # Default to system error
        return ErrorCategory.SYSTEM_ERROR
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """
        Determine if error should be retried
        
        Args:
            error: Exception that occurred
            attempt: Current attempt number (1-indexed)
            
        Returns:
            True if should retry
        """
        if attempt >= self.max_retries:
            return False
        
        category = self.categorize_error(error)
        return category in [ErrorCategory.RETRYABLE, ErrorCategory.RATE_LIMIT]
    
    def get_retry_delay(self, attempt: int, error: Exception) -> float:
        """
        Get retry delay with exponential backoff
        
        Args:
            attempt: Current attempt number
            error: Exception that occurred
            
        Returns:
            Delay in seconds
        """
        category = self.categorize_error(error)
        
        if category == ErrorCategory.RATE_LIMIT:
            # Longer delay for rate limits
            return self.retry_delay * (2 ** attempt) * 2
        else:
            # Exponential backoff for retryable errors
            return self.retry_delay * (2 ** attempt)
    
    async def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic
        
        Args:
            func: Async function to execute
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries fail
        """
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                
                if not self.should_retry(e, attempt):
                    raise
                
                delay = self.get_retry_delay(attempt, e)
                await asyncio.sleep(delay)
        
        # All retries exhausted
        raise last_error
    
    def format_error_response(self, error: Exception, context: Optional[Dict] = None) -> Dict:
        """
        Format error for API response
        
        Args:
            error: Exception
            context: Optional context information
            
        Returns:
            Formatted error response
        """
        category = self.categorize_error(error)
        
        # Track error
        error_key = f"{category.value}:{type(error).__name__}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # User-friendly messages
        user_messages = {
            ErrorCategory.USER_ERROR: "Please check your input and try again.",
            ErrorCategory.RETRYABLE: "Service temporarily unavailable. Please try again in a moment.",
            ErrorCategory.SYSTEM_ERROR: "An internal error occurred. Our team has been notified.",
            ErrorCategory.AUTH_ERROR: "Authentication required. Please check your credentials.",
            ErrorCategory.RATE_LIMIT: "Too many requests. Please wait a moment and try again.",
            ErrorCategory.NOT_FOUND: "The requested information was not found."
        }
        
        response = {
            'error': True,
            'error_type': category.value,
            'message': user_messages.get(category, "An error occurred."),
            'error_id': f"{category.value}_{int(time.time())}"
        }
        
        # Add context if provided
        if context:
            response['context'] = context
        
        # Include error details in development mode (always show for now)
        import os
        # Always include debug info for now to help diagnose issues
        response['debug'] = {
            'error_class': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc()[:1000]  # Limit traceback length
        }
        
        return response
    
    def get_error_stats(self) -> Dict:
        """Get error statistics"""
        return {
            'error_counts': dict(self.error_counts),
            'total_errors': sum(self.error_counts.values())
        }

