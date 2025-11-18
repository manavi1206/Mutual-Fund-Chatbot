"""
Session Storage - Persistent session management with Redis fallback
Enterprise-grade session persistence
"""
import json
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import hashlib


class SessionStorage:
    """Manages persistent session storage with Redis or in-memory fallback"""
    
    def __init__(self, use_redis: bool = False, redis_host: str = "localhost", redis_port: int = 6379, redis_db: int = 0):
        """
        Initialize session storage
        
        Args:
            use_redis: Whether to use Redis (requires redis package)
            redis_host: Redis host
            redis_port: Redis port
            redis_db: Redis database number
        """
        self.use_redis = use_redis
        self.redis_client = None
        
        if use_redis:
            try:
                import redis
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=True
                )
                # Test connection
                self.redis_client.ping()
                print("✓ Redis connected for session storage")
            except ImportError:
                print("⚠️  Redis package not installed, falling back to in-memory storage")
                self.use_redis = False
            except Exception as e:
                print(f"⚠️  Redis connection failed: {e}, falling back to in-memory storage")
                self.use_redis = False
        
        # In-memory fallback
        if not self.use_redis:
            self.memory_store: Dict[str, Dict] = {}
            print("✓ Using in-memory session storage")
    
    def save_session(self, session_id: str, data: Dict, ttl_seconds: int = 3600):
        """
        Save session data
        
        Args:
            session_id: Session identifier
            data: Session data to save
            ttl_seconds: Time to live in seconds (default: 1 hour)
        """
        if self.use_redis and self.redis_client:
            try:
                key = f"session:{session_id}"
                self.redis_client.setex(
                    key,
                    ttl_seconds,
                    json.dumps(data)
                )
            except Exception as e:
                print(f"⚠️  Redis save failed: {e}, using memory fallback")
                self.memory_store[session_id] = {
                    'data': data,
                    'expires_at': datetime.now() + timedelta(seconds=ttl_seconds)
                }
        else:
            self.memory_store[session_id] = {
                'data': data,
                'expires_at': datetime.now() + timedelta(seconds=ttl_seconds)
            }
    
    def load_session(self, session_id: str) -> Optional[Dict]:
        """
        Load session data
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None if not found/expired
        """
        if self.use_redis and self.redis_client:
            try:
                key = f"session:{session_id}"
                data = self.redis_client.get(key)
                if data:
                    return json.loads(data)
            except Exception as e:
                print(f"⚠️  Redis load failed: {e}, trying memory fallback")
                # Fallback to memory
                if session_id in self.memory_store:
                    return self.memory_store[session_id]['data']
        else:
            if session_id in self.memory_store:
                session = self.memory_store[session_id]
                if datetime.now() < session['expires_at']:
                    return session['data']
                else:
                    # Expired, remove it
                    del self.memory_store[session_id]
        
        return None
    
    def delete_session(self, session_id: str):
        """Delete session data"""
        if self.use_redis and self.redis_client:
            try:
                key = f"session:{session_id}"
                self.redis_client.delete(key)
            except Exception as e:
                print(f"⚠️  Redis delete failed: {e}")
        
        if session_id in self.memory_store:
            del self.memory_store[session_id]
    
    def cleanup_expired(self):
        """Clean up expired sessions (for in-memory storage)"""
        if not self.use_redis:
            now = datetime.now()
            expired = [
                sid for sid, session in self.memory_store.items()
                if now >= session['expires_at']
            ]
            for sid in expired:
                del self.memory_store[sid]
            return len(expired)
        return 0

