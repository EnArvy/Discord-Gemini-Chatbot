"""
AI service layer for interacting with Google's Generative AI API.
Handles chat session management and response generation.
"""
import traceback
from typing import Dict, Any, Optional
import google.genai as genai
from google.genai import types
from settings import (
    GOOGLE_AI_KEY,
    BOT_TEMPLATE
)
from storage import log_error


class AIService:
    """Manages interactions with Google's Generative AI API."""
    
    def __init__(self):
        """Initialize the AI service with configuration."""
        # Configure the client with API key
        self.client = genai.Client(api_key=GOOGLE_AI_KEY)
        self.model_name = "gemini-3-flash-preview"
        self.message_history: Dict[int, Any] = {}        # Track conversation history separately since Chat object doesn't expose it
        self.conversation_history: Dict[int, list[Dict[str, Any]]] = {}    
    def _convert_history_to_new_format(self, history: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """
        Convert history format from old library to new library format if needed.
        The new google.genai library requires parts to be structured as dicts with text field.
        
        Args:
            history: Chat history in any format
            
        Returns:
            History in the new library's expected format
        """
        # Ensure history items have 'role' and 'parts' as expected by google.genai
        converted = []
        for item in history:
            if isinstance(item, dict):
                # Normalize the item to have 'role' and 'parts'
                normalized = {}
                if 'role' in item:
                    normalized['role'] = item['role']
                if 'parts' in item:
                    # Ensure parts is a list of properly formatted dicts
                    parts = item['parts']
                    if not isinstance(parts, list):
                        parts = [parts]
                    
                    # Convert each part to proper format
                    formatted_parts = []
                    for part in parts:
                        if isinstance(part, str):
                            # String parts need to be wrapped in a dict with 'text' key
                            formatted_parts.append({"text": part})
                        elif isinstance(part, dict):
                            # If it already has 'text' or is a binary part, keep it
                            formatted_parts.append(part)
                        else:
                            # For other types, convert to string and wrap
                            formatted_parts.append({"text": str(part)})
                    
                    normalized['parts'] = formatted_parts
                if normalized:
                    converted.append(normalized)
        return converted
    
    def load_history(self, history_data: Dict[int, list[Dict[str, Any]]]) -> None:
        """
        Load previously saved chat history.
        Maintains backward compatibility with existing saved data.
        
        Args:
            history_data: Dictionary mapping channel IDs to chat histories
        """
        for channel_id, history in history_data.items():
            try:
                # Convert history to new format for compatibility
                converted_history = self._convert_history_to_new_format(history)
                # Start a new chat session with the converted history
                self.message_history[channel_id] = self.client.chats.create(
                    model=self.model_name,
                    history=converted_history  # type: ignore
                )
                # Store the converted history for persistence
                self.conversation_history[channel_id] = converted_history
            except Exception as e:
                # Log conversion error but don't fail - start fresh instead
                print(f"Warning: Could not load history for channel {channel_id}: {e}")
                self.message_history[channel_id] = self.client.chats.create(
                    model=self.model_name,
                    history=[]
                )
                self.conversation_history[channel_id] = []
    
    def generate_response(self, channel_id: int, attachments: list[Dict[str, Any]], text: str) -> str:
        """
        Generate a response from the AI model for the given input.
        
        Args:
            channel_id: Discord channel ID for context
            attachments: List of attachment data dictionaries
            text: The user's message text
            
        Returns:
            The AI model's response text
            
        Raises:
            Exception: If the API call fails
        """
        response: Optional[types.GenerateContentResponse] = None
        try:
            # Prepare prompt parts - convert attachments to the new format
            prompt_parts: list[Any] = []
            for attachment in attachments:
                prompt_parts.append(attachment)
            prompt_parts.append(text)
            
            # Initialize chat session if not exists
            if channel_id not in self.message_history:
                # Convert BOT_TEMPLATE to new format
                converted_template = self._convert_history_to_new_format(BOT_TEMPLATE)
                self.message_history[channel_id] = self.client.chats.create(
                    model=self.model_name,
                    history=converted_template  # type: ignore
                )
                # Initialize conversation history with template
                self.conversation_history[channel_id] = converted_template.copy()
            
            # Send message to AI - use synchronous send_message (blocking)
            response = self.message_history[channel_id].send_message(prompt_parts)
            
            # Track user message in history (format parts properly for storage)
            if channel_id in self.conversation_history:
                # Convert prompt parts to storable format
                formatted_parts = []
                for part in prompt_parts:
                    if isinstance(part, str):
                        formatted_parts.append({"text": part})
                    else:
                        formatted_parts.append(part)
                
                self.conversation_history[channel_id].append({
                    "role": "user",
                    "parts": formatted_parts
                })
                # Track model response in history
                if response and response.text:
                    self.conversation_history[channel_id].append({
                        "role": "model",
                        "parts": [{"text": response.text}]
                    })
            
            return response.text if response and response.text else ""
            
        except Exception as e:
            # Log detailed error information for debugging
            try:
                history_info = str(self.conversation_history.get(channel_id, [])) if channel_id in self.conversation_history else "N/A"
                candidates = str(response.candidates) if response else "N/A"
                parts = str(response.parts) if response else "N/A"
                prompt_feedback = str(response.prompt_feedback) if response and response.prompt_feedback else "N/A"
            except:
                history_info = "N/A"
                candidates = "N/A"
                parts = "N/A"
                prompt_feedbacks = "N/A"
            
            log_error(
                text=text,
                error_traceback=traceback.format_exc(),
                history=history_info,
                candidates=candidates,
                parts=parts,
                prompt_feedbacks=prompt_feedback
            )
            raise
    
    def reset_channel_history(self, channel_id: int, custom_template: Optional[list[Dict[str, Any]]] = None) -> None:
        """
        Reset the chat history for a channel.
        
        Args:
            channel_id: Discord channel ID
            custom_template: Optional custom initial template for the chat
        """
        if custom_template is None:
            custom_template = BOT_TEMPLATE
        
        # Convert template to new format
        converted_template = self._convert_history_to_new_format(custom_template)
        self.message_history[channel_id] = self.client.chats.create(
            model=self.model_name,
            history=converted_template  # type: ignore
        )
        # Reset conversation history
        self.conversation_history[channel_id] = converted_template.copy()
    
    def delete_channel_history(self, channel_id: int) -> None:
        """
        Delete chat history for a channel.
        
        Args:
            channel_id: Discord channel ID
        """
        if channel_id in self.message_history:
            del self.message_history[channel_id]
        if channel_id in self.conversation_history:
            del self.conversation_history[channel_id]
    
    def get_history(self, channel_id: int) -> list[Dict[str, Any]]:
        """
        Get the chat history for a channel.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            The chat history list
        """
        return self.conversation_history.get(channel_id, [])
