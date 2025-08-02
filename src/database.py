"""
Database module for AI Call Bot application.
Handles all database operations including initialization, conversation management, and search functionality.
"""

import sqlite3
import datetime
from typing import List, Dict, Optional, Any
from flask import g
from config import DATABASE_PATH, PERSONAS

def get_db():
    """Get database connection, creating it if necessary."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """Close database connection if it exists."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database with required tables."""
    # Create a direct database connection for initialization
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    
    # Create conversations table
    db.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            llm_model TEXT,
            tts_voice TEXT,
            persona_key TEXT,
            summary_short TEXT,
            summary_full TEXT
        )
    """)
    
    # Create messages table
    db.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            sender TEXT NOT NULL,
            text TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id)
        )
    """)
    
    # Add any missing columns to conversations table
    try:
        db.execute("ALTER TABLE conversations ADD COLUMN summary_short TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    try:
        db.execute("ALTER TABLE conversations ADD COLUMN summary_full TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    db.commit()
    db.close()

def start_new_conversation() -> int:
    """Start a new conversation and return its ID."""
    from config import OLLAMA_MODEL, TTS_VOICE, CURRENT_PERSONA_KEY
    
    # Create a direct database connection for starting conversations
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    
    cur = db.execute("""
        INSERT INTO conversations (llm_model, tts_voice, persona_key, start_time)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (OLLAMA_MODEL, TTS_VOICE, CURRENT_PERSONA_KEY))
    db.commit()
    conversation_id = cur.lastrowid
    db.close()
    return conversation_id

def insert_message(conversation_id: int, sender: str, text: str):
    """Insert a message into the database."""
    print(f"[DEBUG] 💾 Database: Inserting message from '{sender}' in conversation #{conversation_id}")
    print(f"[DEBUG] 💾 Database: Message text: '{text[:50]}{'...' if len(text) > 50 else ''}'")
    
    # Create a direct database connection for inserting messages
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    
    db.execute("""
        INSERT INTO messages (conversation_id, sender, text, timestamp)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    """, (conversation_id, sender, text))
    db.commit()
    db.close()
    print(f"[DEBUG] 💾 Database: Message inserted successfully")

def get_conversation_text(conv_id: int) -> str:
    """Get all text from a conversation as a single string."""
    db = get_db()
    cur = db.execute("""
        SELECT text FROM messages 
        WHERE conversation_id = ? 
        ORDER BY timestamp ASC
    """, (conv_id,))
    messages = cur.fetchall()
    return "\n".join([row["text"] for row in messages])

def search_conversations(query: str, threshold: float) -> List[Dict[str, Any]]:
    """Search conversations using TF-IDF and cosine similarity."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    
    db = get_db()
    
    # Get all conversations with their text
    cur = db.execute("""
        SELECT c.id, c.start_time, GROUP_CONCAT(m.text, ' ') as full_text
        FROM conversations c
        LEFT JOIN messages m ON c.id = m.conversation_id
        GROUP BY c.id
        HAVING full_text IS NOT NULL
    """)
    conversations = cur.fetchall()
    
    if not conversations:
        return []
    
    # Prepare documents for TF-IDF
    docs = [conv["full_text"] for conv in conversations]
    docs.append(query)  # Add query as last document
    
    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
    tfidf_matrix = vectorizer.fit_transform(docs)
    
    # Calculate similarities
    query_vector = tfidf_matrix[-1]  # Last document is the query
    doc_vectors = tfidf_matrix[:-1]  # All documents except query
    
    similarities = cosine_similarity(query_vector, doc_vectors).flatten()
    
    # Filter and format results
    results = []
    for i, similarity in enumerate(similarities):
        if similarity >= threshold:
            conv = conversations[i]
            # Get a snippet (first 200 chars of the conversation)
            snippet = conv["full_text"][:200] + "..." if len(conv["full_text"]) > 200 else conv["full_text"]
            
            results.append({
                "conv_id": conv["id"],
                "start_time": conv["start_time"],
                "similarity": float(similarity),
                "snippet": snippet
            })
    
    # Sort by similarity (highest first)
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results

def generate_and_store_summary(conv_id: int):
    """Generate and store conversation summaries."""
    from .llm_client import query_ollama
    
    db = get_db()
    
    # Get conversation text
    conversation_text = get_conversation_text(conv_id)
    if not conversation_text.strip():
        return
    
    # Generate short summary
    short_prompt = f"Summarize this conversation in 2-3 sentences:\n\n{conversation_text}"
    try:
        short_summary = query_ollama(short_prompt)
        if short_summary and len(short_summary) > 10:
            # Clean up the summary
            short_summary = short_summary.strip()
            if short_summary.startswith("Summary:"):
                short_summary = short_summary[8:].strip()
    except Exception as e:
        print(f"[ERROR] Failed to generate short summary: {e}")
        short_summary = "Conversation summary unavailable."
    
    # Generate full summary
    full_prompt = f"""Please provide a detailed summary of this conversation, including:
1. Main topics discussed
2. Key points or decisions made
3. Any important details or context

Conversation:
{conversation_text}"""
    
    try:
        full_summary = query_ollama(full_prompt)
        if full_summary and len(full_summary) > 20:
            full_summary = full_summary.strip()
        else:
            full_summary = "Detailed summary unavailable."
    except Exception as e:
        print(f"[ERROR] Failed to generate full summary: {e}")
        full_summary = "Detailed summary unavailable."
    
    # Store summaries
    db.execute("""
        UPDATE conversations 
        SET summary_short = ?, summary_full = ?
        WHERE id = ?
    """, (short_summary, full_summary, conv_id))
    db.commit()

def get_conversation_metadata(conv_id: int) -> Optional[Dict[str, Any]]:
    """Get metadata for a specific conversation."""
    db = get_db()
    cur = db.execute("""
        SELECT start_time, llm_model, tts_voice, persona_key, summary_full
        FROM conversations
        WHERE id = ?
    """, (conv_id,))
    row = cur.fetchone()
    
    if not row:
        return None
    
    return {
        "start_time": row["start_time"],
        "llm_model": row["llm_model"],
        "tts_voice": row["tts_voice"],
        "persona_key": row["persona_key"],
        "summary_full": row["summary_full"]
    }

def get_conversation_messages(conv_id: int) -> List[Dict[str, Any]]:
    """Get all messages for a conversation."""
    db = get_db()
    cur = db.execute("""
        SELECT sender, text, timestamp
        FROM messages
        WHERE conversation_id = ?
        ORDER BY timestamp ASC
    """, (conv_id,))
    
    messages = []
    for row in cur.fetchall():
        messages.append({
            "sender": row["sender"],
            "text": row["text"],
            "timestamp": row["timestamp"]
        })
    
    return messages

def get_all_conversations() -> List[Dict[str, Any]]:
    """Get all conversations with metadata."""
    db = get_db()
    cur = db.execute("""
        SELECT id, start_time, llm_model, tts_voice, persona_key, summary_short
        FROM conversations
        ORDER BY start_time DESC
    """)
    
    conversations = []
    for row in cur.fetchall():
        conversations.append({
            "id": row["id"],
            "start_time": row["start_time"],
            "llm_model": row["llm_model"],
            "tts_voice": row["tts_voice"],
            "persona_key": row["persona_key"],
            "summary_short": row["summary_short"]
        })
    
    return conversations 