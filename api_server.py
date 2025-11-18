"""
FastAPI server for Enterprise-Grade RAG system
All phases integrated: UX, Safety, Observability, Architecture, Wow Factors
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import json
import time

# Load environment variables from .env file if available (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()  # This will load .env file if it exists
except ImportError:
    # python-dotenv not installed, skip (will use system env vars)
    pass

# Load configuration
from config_loader import get_config
config = get_config()

from rag_system import RAGSystem
from metrics_collector import MetricsCollector
from access_control import UserRole
from structured_logger import StructuredLogger, get_logger, generate_request_id
from enhanced_error_handler import EnhancedErrorHandler
from simple_cache import SimpleCache
from fastapi import Request
import asyncio
import hashlib
from datetime import datetime
import os

app = FastAPI(title="HDFC MF Chatbot API - Enterprise Edition")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to catch all unhandled exceptions"""
    import traceback
    error_trace = traceback.format_exc()
    
    try:
        logger = get_logger()
        logger.error(f"Unhandled exception: {str(exc)}",
                    endpoint=str(request.url),
                    traceback=error_trace[:500])
    except:
        pass  # Don't fail if logging fails
    
    try:
        error_response = error_handler.format_error_response(exc, {
            'endpoint': str(request.url),
            'method': request.method
        })
    except:
        # Fallback if error handler fails
        error_response = {
            'message': 'An internal error occurred',
            'debug': {
                'error_class': type(exc).__name__,
                'error_message': str(exc),
                'traceback': error_trace[:1000]
            }
        }
    
    # Use proper HTTP status code (500 for server errors)
    # Only include debug info in non-production
    response_content = {
        "answer": f"I encountered an error processing your query. {error_response.get('message', 'Please try again.')}",
        "source_url": None,
        "refused": False,
        "query_type": "general",
        "error": True,
        "error_message": error_response.get('message', 'An error occurred')
    }
    
    # Only include debug info in development
    if not config.is_production:
        response_content["debug"] = error_response.get('debug', {})
    
    return JSONResponse(
        status_code=500,  # Proper HTTP status code
        content=response_content
    )

# CORS middleware - restrict in production (from config)
allowed_origins = config.allowed_origins
if config.is_production and "*" in allowed_origins:
    # In production, don't allow all origins
    allowed_origins = [os.getenv("ALLOWED_ORIGIN", "https://groww.in")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# Initialize components
rag = None
metrics_collector = MetricsCollector()

# Initialize enhanced components
logger = get_logger()
error_handler = EnhancedErrorHandler(max_retries=3, retry_delay=1.0)

# Initialize simple cache with Redis support (from config)
cache = None
if config.get('cache.enabled', True):
    # Check if Redis is enabled via config or environment
    use_redis = config.get_with_env('redis.enabled', 'REDIS_ENABLED', False)
    redis_host = config.get_with_env('redis.host', 'REDIS_HOST', 'localhost')
    redis_port = config.get_with_env('redis.port', 'REDIS_PORT', 6379)
    redis_db = config.get('redis.db', 1)
    
    cache = SimpleCache(
        max_size=config.get('cache.max_size', 100),
        ttl_seconds=config.get('cache.ttl_seconds', 3600),
        use_redis=use_redis,
        redis_host=redis_host,
        redis_port=redis_port,
        redis_db=redis_db
    )

@app.on_event("startup")
async def startup_event():
    global rag
    logger.info("Initializing RAG system...", event="system_startup")
    rag = RAGSystem()
    logger.info("RAG system ready!", event="system_startup")
    print("✓ RAG system ready!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down gracefully", event="system_shutdown")

# Request/Response Models
class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 3
    session_id: Optional[str] = "default"
    response_style: Optional[str] = "default"  # "default", "brief", "detailed", "beginner"
    stream: Optional[bool] = False
    user_role: Optional[str] = "PUBLIC"  # "PUBLIC", "CUSTOMER", "SUPPORT", "ADMIN"

# Removed unused request models (simplified codebase):
# - FeedbackRequest (feedback_system removed)
# - FAQRequest (knowledge_manager removed)

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "HDFC Mutual Fund FAQ Chatbot API - Enterprise Edition",
        "version": "2.0.0",
        "features": [
            "Advanced Retrieval",
            "Conversation Intelligence",
            "Progressive Responses",
            "Safety & Security",
            "Observability",
            "Multi-tenant Support",
            "Proactive Assistant"
        ]
    }

@app.get("/health")
async def health():
    """Enhanced health check with component status"""
    health_status = {
        "status": "healthy",
        "rag_initialized": rag is not None,
        "components": {
            "metrics": True,
            "cache": cache.get_stats() if cache else {"enabled": False},
            "error_handler": error_handler.get_error_stats()
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # Check if any critical component is down
    if not rag:
        health_status["status"] = "degraded"
        health_status["issues"] = ["RAG system not initialized"]
    
    return health_status

@app.post("/api/query")
async def query(request: Request, query_request: QueryRequest):
    """Query the RAG system with all enterprise features"""
    # Generate request ID for tracking
    request_id = generate_request_id()
    logger.set_request_id(request_id)
    
    start_time = time.time()
    
    if not rag:
        error_response = error_handler.format_error_response(
            Exception("System is initializing"),
            {'endpoint': '/api/query'}
        )
        logger.error("System is not ready", request_id=request_id)
        raise HTTPException(status_code=503, detail=error_response['message'])
    
    try:
        # Convert user_role string to enum
        role_map = {
            "PUBLIC": UserRole.PUBLIC,
            "CUSTOMER": UserRole.CUSTOMER,
            "SUPPORT": UserRole.SUPPORT,
            "ADMIN": UserRole.ADMIN,
            "INTERNAL": UserRole.INTERNAL
        }
        user_role = role_map.get(query_request.user_role.upper(), UserRole.PUBLIC)
        
        # Check cache first (only for non-streaming requests)
        if not query_request.stream and cache:
            try:
                cache_key = f"query:{hashlib.md5(query_request.query.encode()).hexdigest()}:{query_request.response_style}"
                cached_result = cache.get(cache_key)
                if cached_result:
                    logger.info("Cache hit for query", request_id=request_id, cache_key=cache_key)
                    cached_result['request_id'] = request_id
                    cached_result['cached'] = True
                    return cached_result
            except Exception as e:
                logger.warning(f"Cache lookup failed: {str(e)}", request_id=request_id)
                # Continue without cache if lookup fails
        
        # Streaming removed (simplified codebase)
        # if query_request.stream:
        #     return StreamingResponse(...)
        
        # Regular query with error handling
        try:
            # rag.query is synchronous, so we run it in executor to avoid blocking
            import asyncio
            
            # Create a proper function to pass to executor (lambda has closure issues)
            def run_query():
                return rag.query(
                    user_query=query_request.query,
                    top_k=query_request.top_k,
                    session_id=query_request.session_id,
                    response_style=query_request.response_style,
                    user_role=user_role
                )
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, run_query)
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Query processing error: {str(e)}",
                        request_id=request_id,
                        query=query_request.query[:100],
                        session_id=query_request.session_id,
                        traceback=error_trace[:500])
            
            # Return a user-friendly error response instead of raising
            error_response = error_handler.format_error_response(e, {
                'request_id': request_id,
                'endpoint': '/api/query'
            })
            
            response = {
                "answer": f"I encountered an error processing your query. {error_response.get('message', 'Please try again.')}",
                "source_url": None,
                "refused": False,
                "query_type": "general",
                "error": True,
                "error_message": error_response.get('message', 'An error occurred'),
                "request_id": request_id,
                "response_time_seconds": round(time.time() - start_time, 3)
            }
            # Include debug info if available
            if 'debug' in error_response:
                response['debug'] = error_response['debug']
            return response
        
        response_time = time.time() - start_time
        
        # Record metrics (only if not an error)
        if not result.get("error", False):
            try:
                metrics_collector.record_query(
                    query_request.query,
                    result.get("query_type", "general"),
                    response_time,
                    result.get("chunks_used", 0),
                    query_request.session_id
                )
            except Exception as e:
                logger.warning(f"Failed to record query metrics: {str(e)}", request_id=request_id)
        
        # Record answer quality (only if not an error)
        if not result.get("error", False):
            try:
                metrics_collector.record_answer_quality(
                    query_request.query,
                    result.get("answer", ""),
                    bool(result.get("source_url")),
                    result.get("confidence")
                )
            except Exception as e:
                logger.warning(f"Failed to record answer quality: {str(e)}", request_id=request_id)
        
        # Log query processing
        logger.info(f"Query processed: {query_request.query[:100]}",
                   query=query_request.query[:100],
                   session_id=query_request.session_id,
                   response_time_seconds=round(response_time, 3),
                   query_type=result.get("query_type", "general"),
                   chunks_used=result.get("chunks_used", 0),
                   request_id=request_id)
        
        # Format answer (simplified - removed response_formatter)
        formatted_answer = result.get("answer", "")
        
        response = {
            "answer": formatted_answer,
            "source_url": result.get("source_url"),
            "refused": result.get("refused", False),
            "query_type": result.get("query_type", "general"),
            "chunks_used": result.get("chunks_used", 0),
            "session_id": result.get("session_id", query_request.session_id),
            "suggested_followups": result.get("suggested_followups", []),
            "proactive_suggestions": result.get("proactive_suggestions", []),
            "conversation_summary": result.get("conversation_summary", ""),
            "needs_clarification": result.get("needs_clarification", False),
            "response_time_seconds": round(response_time, 3),
            "request_id": request_id,
            "cached": False
        }
        
        # Add optional fields
        if "confidence" in result:
            response["confidence"] = result["confidence"]
        if "safety_flags" in result:
            response["safety_flags"] = result["safety_flags"]
        if "insights" in result:
            response["insights"] = result["insights"]
        
        # Cache the result (cache for 1 hour) - only if not an error
        if not response.get('error', False) and not query_request.stream and cache:
            try:
                cache_key = f"query:{hashlib.md5(query_request.query.encode()).hexdigest()}:{query_request.response_style}"
                cache.set(cache_key, response, ttl=config.cache_ttl)
            except Exception as e:
                logger.warning(f"Cache write failed: {str(e)}", request_id=request_id)
                # Continue even if cache write fails
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        metrics_collector.record_error("query_error", str(e))
        logger.error(f"Query endpoint error: {str(e)}",
                    request_id=request_id,
                    endpoint='/api/query',
                    query=query_request.query[:100] if hasattr(query_request, 'query') else 'unknown',
                    traceback=error_trace[:500])
        
        # Return error response instead of raising HTTPException
        error_response = error_handler.format_error_response(e, {
            'request_id': request_id,
            'endpoint': '/api/query'
        })
        
        response = {
            "answer": f"I encountered an error processing your query. {error_response.get('message', 'Please try again.')}",
            "source_url": None,
            "refused": False,
            "query_type": "general",
            "error": True,
            "error_message": error_response.get('message', 'An error occurred'),
            "request_id": request_id,
            "response_time_seconds": round(time.time() - start_time, 3)
        }
        # Include debug info if available
        if 'debug' in error_response:
            response['debug'] = error_response['debug']
        return response

# Removed unused endpoints (simplified codebase):
# - /api/feedback (feedback_system removed)
# - /api/feedback/summary (feedback_system removed)
# - /api/evaluate (evaluation_framework not used)
# - /api/knowledge/faqs (knowledge_manager removed)
# - /api/knowledge/faq (knowledge_manager removed)
# - /api/insights/{session_id} (proactive_assistant removed)
# - stream_query (streaming_handler removed)

@app.get("/api/metrics")
async def get_metrics():
    """Get system metrics"""
    try:
        return metrics_collector.get_metrics_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.server_host, port=config.server_port)
