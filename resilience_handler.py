"""
Resilience Handler - Graceful degradation, fallbacks, retries
Enterprise-grade architecture
"""
from typing import Optional, Callable, Any
import time
from functools import wraps


class ResilienceHandler:
    """Handles resilience patterns: retries, fallbacks, circuit breakers"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize resilience handler
        
        Args:
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries (seconds)
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.circuit_breaker_state = {}  # service_name -> state
    
    def retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Retry a function with exponential backoff
        
        Args:
            func: Function to retry
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    time.sleep(delay)
                else:
                    raise last_exception
        
        raise last_exception
    
    def with_fallback(self, primary_func: Callable, fallback_func: Callable,
                     *args, **kwargs) -> Any:
        """
        Execute function with fallback
        
        Args:
            primary_func: Primary function to try
            fallback_func: Fallback function
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Result from primary or fallback
        """
        try:
            return primary_func(*args, **kwargs)
        except Exception as e:
            # Try fallback
            try:
                return fallback_func(*args, **kwargs)
            except Exception as fallback_error:
                # Both failed, raise original error
                raise e
    
    def circuit_breaker(self, service_name: str, threshold: int = 5,
                      timeout: float = 60.0):
        """
        Circuit breaker decorator
        
        Args:
            service_name: Name of service
            threshold: Failure threshold
            timeout: Timeout before retry (seconds)
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                state = self.circuit_breaker_state.get(service_name, {
                    'failures': 0,
                    'last_failure': None,
                    'state': 'closed'  # closed, open, half-open
                })
                
                # Check if circuit is open
                if state['state'] == 'open':
                    if time.time() - state['last_failure'] > timeout:
                        # Try half-open
                        state['state'] = 'half-open'
                    else:
                        raise Exception(f"Circuit breaker open for {service_name}")
                
                try:
                    result = func(*args, **kwargs)
                    # Success - reset failures
                    if state['state'] == 'half-open':
                        state['state'] = 'closed'
                    state['failures'] = 0
                    return result
                except Exception as e:
                    state['failures'] += 1
                    state['last_failure'] = time.time()
                    
                    if state['failures'] >= threshold:
                        state['state'] = 'open'
                    
                    raise e
                finally:
                    self.circuit_breaker_state[service_name] = state
            
            return wrapper
        return decorator
    
    def graceful_degradation(self, primary_func: Callable,
                            degraded_func: Optional[Callable] = None,
                            *args, **kwargs) -> Any:
        """
        Execute with graceful degradation
        
        Args:
            primary_func: Primary function
            degraded_func: Degraded function (optional)
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Result or degraded result
        """
        try:
            return primary_func(*args, **kwargs)
        except Exception as e:
            if degraded_func:
                try:
                    return degraded_func(*args, **kwargs)
                except:
                    pass
            
            # Return minimal response
            return {
                'answer': 'I apologize, but I encountered an issue processing your request. Please try again later.',
                'source_url': None,
                'refused': False,
                'degraded': True,
                'error': str(e)
            }

