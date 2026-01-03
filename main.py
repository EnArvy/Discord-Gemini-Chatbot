"""
Main entry point for the Discord Gemini Chatbot.
Initializes and runs the Discord bot.
"""
import discord
from discord.ext import commands

from settings import (
    DISCORD_BOT_TOKEN,
    BOT_PREFIX,
    BOT_ACTIVITY,
)
from ai_service import AIService
from storage import ChatDataManager
from message_handler import handle_message
from commands import setup_commands, TrackedThreadsManager


class GeminiBot:
    """Main bot class managing initialization and event handling."""
    
    def __init__(self):
        """Initialize the bot and all services."""
        # Setup Discord bot
        intents = discord.Intents.default()
        intents.message_content = True
        
        self.bot = commands.Bot(
            command_prefix=BOT_PREFIX,
            intents=intents,
            help_command=None,
            activity=discord.Game(BOT_ACTIVITY)
        )
        
        # Initialize services
        self.ai_service = AIService()
        self.storage_manager = ChatDataManager()
        self.threads_manager = TrackedThreadsManager()
        
        # Load persisted data
        self._load_persisted_data()
        
        # Register event handlers
        self._register_event_handlers()
        
        # Setup commands
        setup_commands(self.bot, self.ai_service, self.threads_manager)
    
    def _load_persisted_data(self) -> None:
        """Load previously saved data from storage."""
        # Load chat history
        history_data = ChatDataManager.load_chat_history()
        self.ai_service.load_history(history_data)
        
        # Load tracked threads
        self.threads_manager.threads = ChatDataManager.load_tracked_threads()
    
    def _register_event_handlers(self) -> None:
        """Register bot event handlers."""
        
        @self.bot.event
        async def on_ready():
            """Called when the bot has successfully connected to Discord."""
            await self.bot.tree.sync()
            print("----------------------------------------")
            print(f'Gemini Bot Logged in as {self.bot.user}')
            print("----------------------------------------")
        
        @self.bot.event
        async def on_message(message: discord.Message):
            """Called when a message is sent in a channel the bot can see."""
            await handle_message(message, self.ai_service, self.storage_manager)
    
    def run(self) -> None:
        """Start the bot."""
        if DISCORD_BOT_TOKEN:
            self.bot.run(DISCORD_BOT_TOKEN)
        else:
            raise ValueError("DISCORD_BOT_TOKEN environment variable is not set")


def main():
    """Main entry point."""
    bot = GeminiBot()
    bot.run()


if __name__ == '__main__':
    main()
