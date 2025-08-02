"""
Monitoring module for AI Call Bot application.
Handles system health checks, performance metrics, and logging.
"""

import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from threading import Lock
import sqlite3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """System performance metrics."""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    timestamp: datetime

@dataclass
class ConversationMetrics:
    """Conversation-related metrics."""
    total_conversations: int
    active_conversations: int
    avg_conversation_duration: float
    total_messages: int
    avg_messages_per_conversation: float
    timestamp: datetime

@dataclass
class AIMetrics:
    """AI/LLM performance metrics."""
    avg_response_time: float
    total_queries: int
    successful_queries: int
    failed_queries: int
    avg_tokens_per_response: float
    timestamp: datetime

class MonitoringManager:
    """Manages system monitoring and metrics collection."""
    
    def __init__(self):
        self.metrics_lock = Lock()
        self.system_metrics: List[SystemMetrics] = []
        self.conversation_metrics: List[ConversationMetrics] = []
        self.ai_metrics: List[AIMetrics] = []
        self.start_time = datetime.now()
        
        # Performance tracking
        self.response_times: List[float] = []
        self.error_counts: Dict[str, int] = {}
        
        # Initialize monitoring tables
        self._init_monitoring_db()
    
    def _init_monitoring_db(self):
        """Initialize monitoring database tables."""
        db = sqlite3.connect('conversations.db')
        
        # System metrics table
        db.execute("""
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpu_percent REAL,
                memory_percent REAL,
                disk_usage_percent REAL,
                network_bytes_sent INTEGER,
                network_bytes_recv INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Conversation metrics table
        db.execute("""
            CREATE TABLE IF NOT EXISTS conversation_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                total_conversations INTEGER,
                active_conversations INTEGER,
                avg_conversation_duration REAL,
                total_messages INTEGER,
                avg_messages_per_conversation REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # AI metrics table
        db.execute("""
            CREATE TABLE IF NOT EXISTS ai_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                avg_response_time REAL,
                total_queries INTEGER,
                successful_queries INTEGER,
                failed_queries INTEGER,
                avg_tokens_per_response REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Error log table
        db.execute("""
            CREATE TABLE IF NOT EXISTS error_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                error_type TEXT NOT NULL,
                error_message TEXT,
                stack_trace TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        db.commit()
        db.close()
    
    def collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_usage_percent=disk.percent,
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                timestamp=datetime.now()
            )
            
            with self.metrics_lock:
                self.system_metrics.append(metrics)
                # Keep only last 1000 metrics
                if len(self.system_metrics) > 1000:
                    self.system_metrics = self.system_metrics[-1000:]
            
            # Store in database
            self._store_system_metrics(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return None
    
    def collect_conversation_metrics(self) -> ConversationMetrics:
        """Collect conversation-related metrics."""
        try:
            db = sqlite3.connect('conversations.db')
            
            # Get total conversations
            cur = db.execute("SELECT COUNT(*) FROM conversations")
            total_conversations = cur.fetchone()[0]
            
            # Get active conversations (last 24 hours)
            cur = db.execute("""
                SELECT COUNT(*) FROM conversations 
                WHERE start_time > datetime('now', '-1 day')
            """)
            active_conversations = cur.fetchone()[0]
            
            # Get average conversation duration
            cur = db.execute("""
                SELECT AVG(
                    (julianday(end_time) - julianday(start_time)) * 24 * 60
                ) FROM conversations WHERE end_time IS NOT NULL
            """)
            avg_duration = cur.fetchone()[0] or 0
            
            # Get total messages
            cur = db.execute("SELECT COUNT(*) FROM messages")
            total_messages = cur.fetchone()[0]
            
            # Get average messages per conversation
            avg_messages = total_messages / max(total_conversations, 1)
            
            metrics = ConversationMetrics(
                total_conversations=total_conversations,
                active_conversations=active_conversations,
                avg_conversation_duration=avg_duration,
                total_messages=total_messages,
                avg_messages_per_conversation=avg_messages,
                timestamp=datetime.now()
            )
            
            with self.metrics_lock:
                self.conversation_metrics.append(metrics)
                if len(self.conversation_metrics) > 1000:
                    self.conversation_metrics = self.conversation_metrics[-1000:]
            
            # Store in database
            self._store_conversation_metrics(metrics)
            
            db.close()
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting conversation metrics: {e}")
            return None
    
    def collect_ai_metrics(self) -> AIMetrics:
        """Collect AI/LLM performance metrics."""
        try:
            with self.metrics_lock:
                avg_response_time = sum(self.response_times) / max(len(self.response_times), 1)
                total_queries = len(self.response_times)
                successful_queries = total_queries - sum(self.error_counts.values())
                failed_queries = sum(self.error_counts.values())
                avg_tokens = 150  # Placeholder - would need to track actual token usage
            
            metrics = AIMetrics(
                avg_response_time=avg_response_time,
                total_queries=total_queries,
                successful_queries=successful_queries,
                failed_queries=failed_queries,
                avg_tokens_per_response=avg_tokens,
                timestamp=datetime.now()
            )
            
            with self.metrics_lock:
                self.ai_metrics.append(metrics)
                if len(self.ai_metrics) > 1000:
                    self.ai_metrics = self.ai_metrics[-1000:]
            
            # Store in database
            self._store_ai_metrics(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting AI metrics: {e}")
            return None
    
    def record_response_time(self, response_time: float):
        """Record an AI response time."""
        with self.metrics_lock:
            self.response_times.append(response_time)
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-1000:]
    
    def record_error(self, error_type: str, error_message: str, stack_trace: str = None):
        """Record an error occurrence."""
        with self.metrics_lock:
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        # Log to database
        self._store_error_log(error_type, error_message, stack_trace)
        logger.error(f"{error_type}: {error_message}")
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        try:
            # Collect current metrics
            system_metrics = self.collect_system_metrics()
            conversation_metrics = self.collect_conversation_metrics()
            ai_metrics = self.collect_ai_metrics()
            
            # Determine health status
            health_status = "healthy"
            warnings = []
            
            if system_metrics:
                if system_metrics.cpu_percent > 80:
                    health_status = "warning"
                    warnings.append("High CPU usage")
                
                if system_metrics.memory_percent > 85:
                    health_status = "warning"
                    warnings.append("High memory usage")
                
                if system_metrics.disk_usage_percent > 90:
                    health_status = "critical"
                    warnings.append("Disk space critical")
            
            if ai_metrics and ai_metrics.failed_queries > 0:
                failure_rate = ai_metrics.failed_queries / ai_metrics.total_queries
                if failure_rate > 0.1:  # 10% failure rate
                    health_status = "warning"
                    warnings.append("High AI query failure rate")
            
            uptime = datetime.now() - self.start_time
            
            return {
                "status": health_status,
                "uptime_seconds": uptime.total_seconds(),
                "warnings": warnings,
                "system_metrics": system_metrics.__dict__ if system_metrics else None,
                "conversation_metrics": conversation_metrics.__dict__ if conversation_metrics else None,
                "ai_metrics": ai_metrics.__dict__ if ai_metrics else None
            }
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _store_system_metrics(self, metrics: SystemMetrics):
        """Store system metrics in database."""
        db = sqlite3.connect('conversations.db')
        db.execute("""
            INSERT INTO system_metrics 
            (cpu_percent, memory_percent, disk_usage_percent, network_bytes_sent, network_bytes_recv)
            VALUES (?, ?, ?, ?, ?)
        """, (metrics.cpu_percent, metrics.memory_percent, metrics.disk_usage_percent,
              metrics.network_bytes_sent, metrics.network_bytes_recv))
        db.commit()
        db.close()
    
    def _store_conversation_metrics(self, metrics: ConversationMetrics):
        """Store conversation metrics in database."""
        db = sqlite3.connect('conversations.db')
        db.execute("""
            INSERT INTO conversation_metrics 
            (total_conversations, active_conversations, avg_conversation_duration, 
             total_messages, avg_messages_per_conversation)
            VALUES (?, ?, ?, ?, ?)
        """, (metrics.total_conversations, metrics.active_conversations, metrics.avg_conversation_duration,
              metrics.total_messages, metrics.avg_messages_per_conversation))
        db.commit()
        db.close()
    
    def _store_ai_metrics(self, metrics: AIMetrics):
        """Store AI metrics in database."""
        db = sqlite3.connect('conversations.db')
        db.execute("""
            INSERT INTO ai_metrics 
            (avg_response_time, total_queries, successful_queries, failed_queries, avg_tokens_per_response)
            VALUES (?, ?, ?, ?, ?)
        """, (metrics.avg_response_time, metrics.total_queries, metrics.successful_queries,
              metrics.failed_queries, metrics.avg_tokens_per_response))
        db.commit()
        db.close()
    
    def _store_error_log(self, error_type: str, error_message: str, stack_trace: str = None):
        """Store error log in database."""
        db = sqlite3.connect('conversations.db')
        db.execute("""
            INSERT INTO error_log (error_type, error_message, stack_trace)
            VALUES (?, ?, ?)
        """, (error_type, error_message, stack_trace))
        db.commit()
        db.close()

# Global monitoring manager instance
monitoring_manager = MonitoringManager() 