"""
AI service layer for interacting with Google's Generative AI API.
Handles chat session management and response generation.
"""
import traceback
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from settings import (
    GOOGLE_AI_KEY,
    TEXT_GENERATION_CONFIG,
    SAFETY_SETTINGS,
    BOT_TEMPLATE
)
from storage import log_error


class AIService:
    """Manages interactions with Google's Generative AI API."""
    
    def __init__(self):
        """Initialize the AI service with configuration."""
        genai.configure(api_key=GOOGLE_AI_KEY)  # type: ignore
        self.model = genai.GenerativeModel(  # type: ignore
            model_name="gemini-3-flash-preview",
            generation_config=TEXT_GENERATION_CONFIG,  # type: ignore
            safety_settings=SAFETY_SETTINGS
        )
        self.message_history: Dict[int, Any] = {}
    
    def load_history(self, history_data: Dict[int, List[Dict[str, Any]]]) -> None:
        """
        Load previously saved chat history.
        
        Args:
            history_data: Dictionary mapping channel IDs to chat histories
        """
        for channel_id, history in history_data.items():
            self.message_history[channel_id] = self.model.start_chat(history=history)  # type: ignore
    
    async def generate_response(self, channel_id: int, attachments: List[Dict[str, Any]], text: str) -> str:
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
        response: Optional[Any] = None
        try:
            # Prepare prompt parts
            prompt_parts: List[Any] = attachments.copy()
            prompt_parts.append(text)
            
            # Initialize chat session if not exists
            if channel_id not in self.message_history:
                self.message_history[channel_id] = self.model.start_chat(history=BOT_TEMPLATE)
            
            # Send message to AI
            response = await self.message_history[channel_id].send_message_async(prompt_parts)
            return response.text if response else ""
            
        except Exception as e:
            # Log detailed error information for debugging
            try:
                history_info = str(self.message_history[channel_id].history)
                candidates = str(response.candidates) if response else "N/A"
                parts = str(response.parts) if response else "N/A"
                prompt_feedbacks = str(response.prompt_feedbacks) if response else "N/A"
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
                prompt_feedbacks=prompt_feedbacks
            )
            raise
    
    def reset_channel_history(self, channel_id: int, custom_template: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Reset the chat history for a channel.
        
        Args:
            channel_id: Discord channel ID
            custom_template: Optional custom initial template for the chat
        """
        if custom_template is None:
            custom_template = BOT_TEMPLATE
        
        self.message_history[channel_id] = self.model.start_chat(history=custom_template)  # type: ignore
    
    def delete_channel_history(self, channel_id: int) -> None:
        """
        Delete chat history for a channel.
        
        Args:
            channel_id: Discord channel ID
        """
        if channel_id in self.message_history:
            del self.message_history[channel_id]
    
    def get_history(self, channel_id: int) -> List[Dict[str, Any]]:
        """
        Get the chat history for a channel.
        
        Args:
            channel_id: Discord channel ID
            
        Returns:
            The chat history list
        """
        if channel_id in self.message_history:
            return self.message_history[channel_id].history
        return []
