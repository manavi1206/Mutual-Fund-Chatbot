"""
Metrics Database - SQLite/PostgreSQL storage for metrics and analytics
Enterprise-grade metrics persistence
"""
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
import json


class MetricsDatabase:
    """Database for storing and querying metrics"""
    
    def __init__(self, db_path: str = "metrics.db", use_postgres: bool = False, postgres_url: Optional[str] = None):
        """
        Initialize metrics database
        
        Args:
            db_path: SQLite database path (if use_postgres=False)
            use_postgres: Whether to use PostgreSQL
            postgres_url: PostgreSQL connection URL
        """
        self.use_postgres = use_postgres
        self.db_path = db_path
        
        if use_postgres and postgres_url:
            try:
                import psycopg2
                from psycopg2.extras import RealDictCursor
                self.conn = psycopg2.connect(postgres_url)
                self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
                self._create_tables_postgres()
                print("✓ PostgreSQL connected for metrics")
            except ImportError:
                print("⚠️  psycopg2 not installed, falling back to SQLite")
                self.use_postgres = False
            except Exception as e:
                print(f"⚠️  PostgreSQL connection failed: {e}, falling back to SQLite")
                self.use_postgres = False
        
        if not self.use_postgres:
            # Use SQLite
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            self._create_tables_sqlite()
            print("✓ SQLite database initialized for metrics")
    
    def _create_tables_sqlite(self):
        """Create tables in SQLite"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT,
                query_type TEXT,
                response_time REAL,
                chunks_used INTEGER,
                session_id TEXT,
                request_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS answer_quality (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT,
                answer_text TEXT,
                has_source INTEGER,
                confidence TEXT,
                quality_score REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                query_text TEXT,
                answer_text TEXT,
                feedback_type TEXT,
                value REAL,
                text_feedback TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT,
                error_message TEXT,
                error_category TEXT,
                context TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_queries_timestamp ON queries(timestamp)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_queries_session ON queries(session_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_timestamp ON feedback(timestamp)")
        
        self.conn.commit()
    
    def _create_tables_postgres(self):
        """Create tables in PostgreSQL"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id SERIAL PRIMARY KEY,
                query_text TEXT,
                query_type TEXT,
                response_time REAL,
                chunks_used INTEGER,
                session_id TEXT,
                request_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS answer_quality (
                id SERIAL PRIMARY KEY,
                query_text TEXT,
                answer_text TEXT,
                has_source BOOLEAN,
                confidence TEXT,
                quality_score REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                session_id TEXT,
                query_text TEXT,
                answer_text TEXT,
                feedback_type TEXT,
                value REAL,
                text_feedback TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS errors (
                id SERIAL PRIMARY KEY,
                error_type TEXT,
                error_message TEXT,
                error_category TEXT,
                context JSONB,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_queries_timestamp ON queries(timestamp)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_queries_session ON queries(session_id)")
        
        self.conn.commit()
    
    def record_query(self, query_text: str, query_type: str, response_time: float,
                    chunks_used: int, session_id: str, request_id: Optional[str] = None):
        """Record a query"""
        if self.use_postgres:
            self.cursor.execute("""
                INSERT INTO queries (query_text, query_type, response_time, chunks_used, session_id, request_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (query_text, query_type, response_time, chunks_used, session_id, request_id))
        else:
            self.cursor.execute("""
                INSERT INTO queries (query_text, query_type, response_time, chunks_used, session_id, request_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (query_text, query_type, response_time, chunks_used, session_id, request_id))
        self.conn.commit()
    
    def record_answer_quality(self, query_text: str, answer_text: str, has_source: bool,
                            confidence: Optional[str], quality_score: Optional[float] = None):
        """Record answer quality"""
        if self.use_postgres:
            self.cursor.execute("""
                INSERT INTO answer_quality (query_text, answer_text, has_source, confidence, quality_score)
                VALUES (%s, %s, %s, %s, %s)
            """, (query_text, answer_text, has_source, confidence, quality_score))
        else:
            self.cursor.execute("""
                INSERT INTO answer_quality (query_text, answer_text, has_source, confidence, quality_score)
                VALUES (?, ?, ?, ?, ?)
            """, (query_text, answer_text, 1 if has_source else 0, confidence, quality_score))
        self.conn.commit()
    
    def record_feedback(self, session_id: str, query_text: str, answer_text: str,
                       feedback_type: str, value: Optional[float] = None, text_feedback: Optional[str] = None):
        """Record feedback"""
        if self.use_postgres:
            self.cursor.execute("""
                INSERT INTO feedback (session_id, query_text, answer_text, feedback_type, value, text_feedback)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session_id, query_text, answer_text, feedback_type, value, text_feedback))
        else:
            self.cursor.execute("""
                INSERT INTO feedback (session_id, query_text, answer_text, feedback_type, value, text_feedback)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, query_text, answer_text, feedback_type, value, text_feedback))
        self.conn.commit()
    
    def record_error(self, error_type: str, error_message: str, error_category: str = "unknown", context: Optional[Dict] = None):
        """Record error"""
        context_json = json.dumps(context) if context else None
        if self.use_postgres:
            self.cursor.execute("""
                INSERT INTO errors (error_type, error_message, error_category, context)
                VALUES (%s, %s, %s, %s::jsonb)
            """, (error_type, error_message, error_category, context_json))
        else:
            self.cursor.execute("""
                INSERT INTO errors (error_type, error_message, error_category, context)
                VALUES (?, ?, ?, ?)
            """, (error_type, error_message, error_category, context_json))
        self.conn.commit()
    
    def get_query_stats(self, days: int = 7) -> Dict:
        """Get query statistics for last N days"""
        cutoff = datetime.now() - timedelta(days=days)
        
        if self.use_postgres:
            self.cursor.execute("""
                SELECT 
                    COUNT(*) as total_queries,
                    AVG(response_time) as avg_response_time,
                    COUNT(DISTINCT session_id) as unique_sessions,
                    COUNT(DISTINCT query_type) as query_types
                FROM queries
                WHERE timestamp >= %s
            """, (cutoff,))
        else:
            self.cursor.execute("""
                SELECT 
                    COUNT(*) as total_queries,
                    AVG(response_time) as avg_response_time,
                    COUNT(DISTINCT session_id) as unique_sessions,
                    COUNT(DISTINCT query_type) as query_types
                FROM queries
                WHERE timestamp >= ?
            """, (cutoff,))
        
        row = self.cursor.fetchone()
        return dict(row) if row else {}
    
    def get_top_queries(self, limit: int = 10, days: int = 7) -> List[Dict]:
        """Get top queries by frequency"""
        cutoff = datetime.now() - timedelta(days=days)
        
        if self.use_postgres:
            self.cursor.execute("""
                SELECT query_text, COUNT(*) as count, AVG(response_time) as avg_time
                FROM queries
                WHERE timestamp >= %s
                GROUP BY query_text
                ORDER BY count DESC
                LIMIT %s
            """, (cutoff, limit))
        else:
            self.cursor.execute("""
                SELECT query_text, COUNT(*) as count, AVG(response_time) as avg_time
                FROM queries
                WHERE timestamp >= ?
                GROUP BY query_text
                ORDER BY count DESC
                LIMIT ?
            """, (cutoff, limit))
        
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]
    
    def close(self):
        """Close database connection"""
        self.conn.close()

