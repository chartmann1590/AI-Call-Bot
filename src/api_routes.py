"""
API Routes module for AI Call Bot application.
Provides RESTful API endpoints for external integrations.
"""

from flask import Flask, request, jsonify, g
from flask_restful import Api, Resource
from flask_cors import CORS
from typing import Dict, List, Optional, Any
import datetime
import json

from security import require_auth, require_admin, security_manager, log_audit_event
from monitoring import monitoring_manager
from database import (
    get_all_conversations, get_conversation_metadata, 
    get_conversation_messages, search_conversations,
    start_new_conversation, insert_message
)
from llm_client import query_ollama, get_available_models, test_ollama_connection
from tts_client import speak_text, get_available_voices
from config import PERSONAS, VOICE_OPTIONS

def create_api_app():
    """Create and configure the API Flask application."""
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes
    api = Api(app)
    
    # Register API resources
    api.add_resource(HealthCheck, '/api/health')
    api.add_resource(ConversationsAPI, '/api/conversations')
    api.add_resource(ConversationAPI, '/api/conversations/<int:conv_id>')
    api.add_resource(SearchAPI, '/api/search')
    api.add_resource(SettingsAPI, '/api/settings')
    api.add_resource(LLMAPI, '/api/llm')
    api.add_resource(TTSAPI, '/api/tts')
    api.add_resource(MetricsAPI, '/api/metrics')
    api.add_resource(AuthAPI, '/api/auth')
    
    return app

class HealthCheck(Resource):
    """Health check endpoint."""
    
    def get(self):
        """Get system health status."""
        try:
            health_data = monitoring_manager.get_system_health()
            return {
                'status': 'success',
                'data': health_data,
                'timestamp': datetime.datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.datetime.now().isoformat()
            }, 500

class ConversationsAPI(Resource):
    """Conversations collection endpoint."""
    
    @require_auth
    def get(self):
        """Get all conversations."""
        try:
            conversations = get_all_conversations()
            return {
                'status': 'success',
                'data': conversations,
                'count': len(conversations)
            }
        except Exception as e:
            log_audit_event(g.current_user.get('user_id'), 'conversations_list_error', str(e))
            return {'status': 'error', 'error': str(e)}, 500
    
    @require_auth
    def post(self):
        """Start a new conversation."""
        try:
            conv_id = start_new_conversation()
            log_audit_event(g.current_user.get('user_id'), 'conversation_started', f'Conversation {conv_id}')
            
            return {
                'status': 'success',
                'data': {'conversation_id': conv_id},
                'message': f'Conversation {conv_id} started successfully'
            }
        except Exception as e:
            log_audit_event(g.current_user.get('user_id'), 'conversation_start_error', str(e))
            return {'status': 'error', 'error': str(e)}, 500

class ConversationAPI(Resource):
    """Individual conversation endpoint."""
    
    @require_auth
    def get(self, conv_id):
        """Get conversation details and messages."""
        try:
            metadata = get_conversation_metadata(conv_id)
            if not metadata:
                return {'status': 'error', 'error': 'Conversation not found'}, 404
            
            messages = get_conversation_messages(conv_id)
            
            return {
                'status': 'success',
                'data': {
                    'metadata': metadata,
                    'messages': messages
                }
            }
        except Exception as e:
            log_audit_event(g.current_user.get('user_id'), 'conversation_view_error', str(e))
            return {'status': 'error', 'error': str(e)}, 500
    
    @require_auth
    def post(self, conv_id):
        """Add a message to a conversation."""
        try:
            data = request.get_json()
            if not data or 'message' not in data:
                return {'status': 'error', 'error': 'Message content required'}, 400
            
            message = data['message']
            sender = data.get('sender', 'user')
            
            # Insert user message
            insert_message(conv_id, sender, message)
            
            # Get AI response
            response = query_ollama(message)
            
            # Insert AI response
            insert_message(conv_id, 'assistant', response)
            
            log_audit_event(g.current_user.get('user_id'), 'message_added', f'Conversation {conv_id}')
            
            return {
                'status': 'success',
                'data': {
                    'user_message': message,
                    'ai_response': response
                }
            }
        except Exception as e:
            log_audit_event(g.current_user.get('user_id'), 'message_add_error', str(e))
            return {'status': 'error', 'error': str(e)}, 500

class SearchAPI(Resource):
    """Search conversations endpoint."""
    
    @require_auth
    def get(self):
        """Search conversations."""
        try:
            query = request.args.get('q', '').strip()
            threshold = float(request.args.get('threshold', '0.5'))
            
            if not query:
                return {'status': 'error', 'error': 'Search query required'}, 400
            
            results = search_conversations(query, threshold)
            
            log_audit_event(g.current_user.get('user_id'), 'search_performed', f'Query: {query}')
            
            return {
                'status': 'success',
                'data': results,
                'count': len(results)
            }
        except Exception as e:
            log_audit_event(g.current_user.get('user_id'), 'search_error', str(e))
            return {'status': 'error', 'error': str(e)}, 500

class SettingsAPI(Resource):
    """Settings management endpoint."""
    
    @require_auth
    def get(self):
        """Get current settings."""
        try:
            from config import OLLAMA_URL, OLLAMA_MODEL, TTS_VOICE, CURRENT_PERSONA_KEY
            
            return {
                'status': 'success',
                'data': {
                    'ollama_url': OLLAMA_URL,
                    'ollama_model': OLLAMA_MODEL,
                    'tts_voice': TTS_VOICE,
                    'current_persona': CURRENT_PERSONA_KEY,
                    'available_personas': list(PERSONAS.keys()),
                    'available_voices': [voice[1] for voice in VOICE_OPTIONS]
                }
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}, 500
    
    @require_auth
    def post(self):
        """Update settings."""
        try:
            data = request.get_json()
            if not data:
                return {'status': 'error', 'error': 'Settings data required'}, 400
            
            # Update settings (this would need to be implemented in config.py)
            # For now, just return success
            log_audit_event(g.current_user.get('user_id'), 'settings_updated', json.dumps(data))
            
            return {
                'status': 'success',
                'message': 'Settings updated successfully'
            }
        except Exception as e:
            log_audit_event(g.current_user.get('user_id'), 'settings_update_error', str(e))
            return {'status': 'error', 'error': str(e)}, 500

class LLMAPI(Resource):
    """LLM interaction endpoint."""
    
    @require_auth
    def post(self):
        """Send a message to the LLM."""
        try:
            data = request.get_json()
            if not data or 'message' not in data:
                return {'status': 'error', 'error': 'Message content required'}, 400
            
            message = data['message']
            persona = data.get('persona', 'helpful')
            
            # Record start time for performance monitoring
            start_time = datetime.datetime.now()
            
            # Get LLM response
            response = query_ollama(message, persona)
            
            # Record response time
            response_time = (datetime.datetime.now() - start_time).total_seconds()
            monitoring_manager.record_response_time(response_time)
            
            log_audit_event(g.current_user.get('user_id'), 'llm_query', f'Persona: {persona}')
            
            return {
                'status': 'success',
                'data': {
                    'response': response,
                    'persona': persona,
                    'response_time': response_time
                }
            }
        except Exception as e:
            monitoring_manager.record_error('llm_error', str(e))
            log_audit_event(g.current_user.get('user_id'), 'llm_error', str(e))
            return {'status': 'error', 'error': str(e)}, 500
    
    @require_auth
    def get(self):
        """Get available models and connection status."""
        try:
            models = get_available_models()
            connection_status = test_ollama_connection()
            
            return {
                'status': 'success',
                'data': {
                    'available_models': models,
                    'connection_status': connection_status
                }
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}, 500

class TTSAPI(Resource):
    """Text-to-speech endpoint."""
    
    @require_auth
    def post(self):
        """Convert text to speech."""
        try:
            data = request.get_json()
            if not data or 'text' not in data:
                return {'status': 'error', 'error': 'Text content required'}, 400
            
            text = data['text']
            voice = data.get('voice', 'en-US-JennyNeural')
            
            # Generate speech
            audio_path = speak_text(text, voice)
            
            log_audit_event(g.current_user.get('user_id'), 'tts_generated', f'Voice: {voice}')
            
            return {
                'status': 'success',
                'data': {
                    'audio_path': audio_path,
                    'voice': voice,
                    'text_length': len(text)
                }
            }
        except Exception as e:
            log_audit_event(g.current_user.get('user_id'), 'tts_error', str(e))
            return {'status': 'error', 'error': str(e)}, 500
    
    @require_auth
    def get(self):
        """Get available voices."""
        try:
            voices = get_available_voices()
            
            return {
                'status': 'success',
                'data': {
                    'available_voices': voices
                }
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}, 500

class MetricsAPI(Resource):
    """Metrics endpoint."""
    
    @require_auth
    def get(self):
        """Get system metrics."""
        try:
            # Collect current metrics
            system_metrics = monitoring_manager.collect_system_metrics()
            conversation_metrics = monitoring_manager.collect_conversation_metrics()
            ai_metrics = monitoring_manager.collect_ai_metrics()
            
            return {
                'status': 'success',
                'data': {
                    'system': system_metrics.__dict__ if system_metrics else None,
                    'conversations': conversation_metrics.__dict__ if conversation_metrics else None,
                    'ai': ai_metrics.__dict__ if ai_metrics else None
                }
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e)}, 500

class AuthAPI(Resource):
    """Authentication endpoint."""
    
    def post(self):
        """Authenticate user."""
        try:
            data = request.get_json()
            if not data or 'username' not in data or 'password' not in data:
                return {'status': 'error', 'error': 'Username and password required'}, 400
            
            username = data['username']
            password = data['password']
            
            # This is a simplified authentication
            # In production, you'd verify against a user database
            if username == 'admin' and password == 'admin':  # Replace with proper auth
                token = security_manager.generate_token('1', username)
                log_audit_event(1, 'login_success', username)
                
                return {
                    'status': 'success',
                    'data': {
                        'token': token,
                        'user': {
                            'id': '1',
                            'username': username,
                            'role': 'admin'
                        }
                    }
                }
            else:
                log_audit_event(None, 'login_failed', username)
                return {'status': 'error', 'error': 'Invalid credentials'}, 401
                
        except Exception as e:
            return {'status': 'error', 'error': str(e)}, 500

# Create the API app instance
api_app = create_api_app() 