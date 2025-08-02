"""
LLM Client module for AI Call Bot application.
Handles all interactions with the Ollama API, including querying and persona management.
"""

import requests
import json
from typing import Optional
from config import OLLAMA_URL, OLLAMA_MODEL, PERSONAS, CURRENT_PERSONA_KEY

def query_ollama(user_text: str, persona_key: Optional[str] = None) -> str:
    """
    Query Ollama with user text and return the response.
    
    Args:
        user_text: The user's input text
        persona_key: Optional persona to use (defaults to CURRENT_PERSONA_KEY)
    
    Returns:
        The LLM response as a string
    """
    if persona_key is None:
        persona_key = CURRENT_PERSONA_KEY
    
    print(f"[DEBUG] 🤖 Ollama: Querying with persona '{persona_key}'")
    print(f"[DEBUG] 🤖 Ollama: User text: '{user_text[:50]}{'...' if len(user_text) > 50 else ''}'")
    
    # Get the persona system instruction
    system_instruction = PERSONAS.get(persona_key, PERSONAS["helpful"])
    print(f"[DEBUG] 🤖 Ollama: Using system instruction (length: {len(system_instruction)} chars)")
    
    # Prepare the request payload
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_instruction
            },
            {
                "role": "user",
                "content": user_text
            }
        ],
        "stream": False
    }
    
    print(f"[DEBUG] 🤖 Ollama: Sending request to {OLLAMA_URL}/api/chat")
    print(f"[DEBUG] 🤖 Ollama: Model: {OLLAMA_MODEL}")
    
    try:
        # Make the request to Ollama
        print(f"[DEBUG] 🤖 Ollama: Making POST request...")
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json=payload,
            timeout=120
        )
        print(f"[DEBUG] 🤖 Ollama: Response status: {response.status_code}")
        response.raise_for_status()
        
        # Parse the response
        print(f"[DEBUG] 🤖 Ollama: Parsing JSON response...")
        data = response.json()
        if "message" in data and "content" in data["message"]:
            response_text = data["message"]["content"].strip()
            print(f"[DEBUG] 🤖 Ollama: Response received (length: {len(response_text)} chars)")
            return response_text
        else:
            print(f"[ERROR] ❌ Unexpected Ollama response format: {data}")
            return "I'm sorry, I couldn't process that request."
            
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] ❌ Ollama request failed: {e}")
        return "I'm sorry, I'm having trouble connecting to my language model right now."
    except json.JSONDecodeError as e:
        print(f"[ERROR] ❌ Failed to parse Ollama response: {e}")
        return "I'm sorry, I received an invalid response from my language model."
    except Exception as e:
        print(f"[ERROR] ❌ Unexpected error in Ollama query: {e}")
        return "I'm sorry, something unexpected happened while processing your request."

def get_available_models() -> list:
    """
    Get list of available Ollama models.
    
    Returns:
        List of model names
    """
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        response.raise_for_status()
        data = response.json()
        models = data.get("models", [])
        return [model.get("name", "") for model in models if model.get("name")]
    except Exception as e:
        print(f"[ERROR] Failed to fetch available models: {e}")
        return []

def test_ollama_connection() -> bool:
    """
    Test if Ollama is accessible and responding.
    
    Returns:
        True if connection is successful, False otherwise
    """
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def get_model_info(model_name: str) -> Optional[dict]:
    """
    Get information about a specific model.
    
    Args:
        model_name: Name of the model to get info for
    
    Returns:
        Model information dictionary or None if not found
    """
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/show",
            json={"name": model_name},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Failed to get model info for {model_name}: {e}")
        return None 