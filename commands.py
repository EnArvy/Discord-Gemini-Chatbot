"""
Discord bot commands for managing conversation history and threads.
"""
from discord import Interaction, app_commands, TextChannel
from discord.ext import commands
from typing import Optional
from settings import BOT_TEMPLATE
from storage import ChatDataManager


def setup_commands(bot: commands.Bot, ai_service, tracked_threads_manager):
    """
    Register all bot commands.
    
    Args:
        bot: The Discord bot instance
        ai_service: The AI service instance
        tracked_threads_manager: Handler for tracked threads
    """
    
    @bot.tree.command(name='forget', description='Forget message history')
    @app_commands.describe(persona='Persona of bot')
    async def forget(interaction: Interaction, persona: Optional[str] = None):
        """
        Clear the conversation history for the current channel.
        Optionally set a new persona for the bot.
        
        Args:
            interaction: The slash command interaction
            persona: Optional new persona for the bot
        """
        try:
            channel_id = interaction.channel_id
            if channel_id is None:
                await interaction.response.send_message("Error: Cannot determine channel.")
                return
            
            # Clear history
            ai_service.delete_channel_history(channel_id)
            ChatDataManager.delete_chat_history(channel_id)
            
            # Reset with new persona if provided
            if persona:
                temp_template = BOT_TEMPLATE.copy()
                temp_template.append({
                    'role': 'user',
                    'parts': [f"Forget what I said earlier! You are {persona}"]
                })
                temp_template.append({
                    'role': 'model',
                    'parts': ["Ok!"]
                })
                ai_service.reset_channel_history(channel_id, temp_template)
                ChatDataManager.save_chat_history(channel_id, ai_service.get_history(channel_id))
            
            await interaction.response.send_message("Message history for channel erased.")
            
        except Exception as e:
            print(f"Error in forget command: {e}")
            await interaction.response.send_message("An error occurred while processing your command.")
    
    @bot.tree.command(
        name='createthread',
        description='Create a thread in which bot will respond to every message.'
    )
    @app_commands.describe(name='Thread name')
    async def create_thread(interaction: Interaction, name: str):
        """
        Create a new thread and add it to tracked threads.
        
        Args:
            interaction: The slash command interaction
            name: The name for the new thread
        """
        try:
            channel = interaction.channel
            if channel is None:
                await interaction.response.send_message("Error: Cannot determine channel.")
                return
            
            if not isinstance(channel, TextChannel):
                await interaction.response.send_message("Error: Can only create threads in text channels.")
                return
            
            thread = await channel.create_thread(
                name=name,
                auto_archive_duration=60
            )
            thread_id = thread.id
            tracked_threads_manager.add_thread(thread_id)
            await interaction.response.send_message(f"Thread {name} created!")
            
        except Exception as e:
            print(f"Error in createthread command: {e}")
            await interaction.response.send_message("Error creating thread!")


class TrackedThreadsManager:
    """Manages tracked threads."""
    
    def __init__(self):
        """Initialize and load tracked threads."""
        self.threads = ChatDataManager.load_tracked_threads()
    
    def add_thread(self, thread_id: int) -> None:
        """
        Add a thread to tracked threads.
        
        Args:
            thread_id: The Discord thread ID
        """
        if thread_id not in self.threads:
            self.threads.append(thread_id)
            self.save()
    
    def remove_thread(self, thread_id: int) -> None:
        """
        Remove a thread from tracked threads.
        
        Args:
            thread_id: The Discord thread ID
        """
        if thread_id in self.threads:
            self.threads.remove(thread_id)
            self.save()
    
    def get_all_threads(self) -> list:
        """Get all tracked thread IDs."""
        return self.threads
    
    def save(self) -> None:
        """Save tracked threads to persistent storage."""
        ChatDataManager.save_tracked_threads(self.threads)
