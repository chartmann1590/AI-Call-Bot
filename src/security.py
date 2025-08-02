"""
Security module for AI Call Bot application.
Handles authentication, authorization, and data protection.
"""

import os
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps
from flask import request, jsonify, g, current_app
import sqlite3
from cryptography.fernet import Fernet

# Security configuration
SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_urlsafe(32))
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())

# Initialize encryption
cipher_suite = Fernet(ENCRYPTION_KEY)

class SecurityManager:
    """Manages security operations including authentication and encryption."""
    
    def __init__(self):
        self.secret_key = SECRET_KEY
        self.cipher_suite = cipher_suite
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt."""
        import bcrypt
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        import bcrypt
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def generate_token(self, user_id: str, username: str) -> str:
        """Generate a JWT token for a user."""
        payload = {
            'user_id': user_id,
            'username': username,
            'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=JWT_ALGORITHM)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self.cipher_suite.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
    
    def sanitize_input(self, text: str) -> str:
        """Sanitize user input to prevent injection attacks."""
        import html
        return html.escape(text.strip())
    
    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

# Global security manager instance
security_manager = SecurityManager()

def require_auth(f):
    """Decorator to require authentication for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        if not token.startswith('Bearer '):
            return jsonify({'error': 'Invalid token format'}), 401
        
        token = token[7:]  # Remove 'Bearer ' prefix
        payload = security_manager.verify_token(token)
        
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        g.current_user = payload
        return f(*args, **kwargs)
    
    return decorated_function

def require_admin(f):
    """Decorator to require admin privileges."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'current_user'):
            return jsonify({'error': 'Authentication required'}), 401
        
        if g.current_user.get('role') != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
        
        return f(*args, **kwargs)
    
    return decorated_function

def rate_limit(max_requests: int = 100, window_seconds: int = 3600):
    """Simple rate limiting decorator."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # This is a basic implementation
            # In production, use Redis or similar for proper rate limiting
            client_ip = request.remote_addr
            # TODO: Implement proper rate limiting logic
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def init_security_db():
    """Initialize security-related database tables."""
    db = sqlite3.connect('conversations.db')
    
    # Users table
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    """)
    
    # Sessions table for tracking active sessions
    db.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Audit log table
    db.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    db.commit()
    db.close()

def log_audit_event(user_id: Optional[int], action: str, details: str = None):
    """Log an audit event."""
    db = sqlite3.connect('conversations.db')
    db.execute("""
        INSERT INTO audit_log (user_id, action, details, ip_address)
        VALUES (?, ?, ?, ?)
    """, (user_id, action, details, request.remote_addr))
    db.commit()
    db.close() 