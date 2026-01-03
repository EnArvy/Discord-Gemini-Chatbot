"""
Handles incoming Discord messages and orchestrates message processing.
"""
import traceback
from discord import Message
from typing import List, Dict, Optional, Any
from attachments import get_attachment_data
from settings import TRACKED_CHANNELS


async def construct_query(message: Message, attachments: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Construct the query string from a Discord message.
    
    Args:
        message: The Discord message
        attachments: Processed attachment data
        
    Returns:
        The formatted query string
    """
    author_name = message.author.name
    
    # Build base query
    if not message.attachments:
        query = f"@{author_name} said \"{message.clean_content}\""
    else:
        if not message.content:
            query = f"@{author_name} sent attachments:"
        else:
            query = f"@{author_name} said \"{message.clean_content}\" while sending attachments:"
    
    # Add quoted message context if replying
    if message.reference is not None:
        reply_message = await message.channel.fetch_message(message.reference.message_id or 0)
        # Only add if not replying to the bot itself
        if reply_message.author.id != message.guild.me.id if message.guild else False:
            query = f"{query} while quoting @{reply_message.author.name} \"{reply_message.clean_content}\""
            
            # Include attachments from quoted message
            if reply_message.attachments and attachments is not None:
                reply_attachments = await get_attachment_data(reply_message.attachments)
                if reply_attachments:
                    attachments.extend(reply_attachments)
    
    return query


async def process_message_attachments(message: Message) -> tuple[List[Dict[str, Any]], bool]:
    """
    Process attachments from a message.
    
    Args:
        message: The Discord message
        
    Returns:
        Tuple of (attachments_list, success_flag)
    """
    if not message.attachments:
        return [], True
    
    attachments = await get_attachment_data(message.attachments)
    
    if attachments is None:
        return [], False
    
    if len(attachments) == 0:
        return [], True  # No supported attachments, but no error
    
    return attachments, True


def should_respond_to_message(message: Message) -> bool:
    """
    Determine if the bot should respond to a message.
    
    Args:
        message: The Discord message
        
    Returns:
        True if bot should respond
    """
    # Don't respond to own messages
    if message.guild and message.guild.me and message.author == message.guild.me:
        return False
    
    # Don't respond to @everyone mentions
    if message.mention_everyone:
        return False
    
    # Check if bot is mentioned, it's a DM, or channel is tracked
    from discord import DMChannel
    bot_user = message.guild.me if message.guild else None
    bot_mentioned = bot_user and bot_user.mentioned_in(message) if bot_user else False
    is_dm = isinstance(message.channel, DMChannel)
    in_tracked_channel = message.channel.id in TRACKED_CHANNELS
    in_tracked_thread = message.channel.id in TRACKED_CHANNELS  # Threads are also in tracked list
    
    return bot_mentioned or is_dm or in_tracked_channel or in_tracked_thread


async def split_and_send_messages(message: Message, text: str, max_length: int) -> None:
    """
    Split a long message into chunks and send them as replies.
    
    Args:
        message: The original Discord message to reply to
        text: The text to send
        max_length: Maximum length of each chunk
    """
    messages = []
    for i in range(0, len(text), max_length):
        sub_message = text[i:i + max_length]
        messages.append(sub_message)
    
    # Send each part as a separate reply
    current_message = message
    for string in messages:
        current_message = await current_message.reply(string)


async def handle_message(message: Message, ai_service, storage_manager) -> None:
    """
    Main message handler orchestrating the processing pipeline.
    
    Args:
        message: The Discord message
        ai_service: The AI service instance
        storage_manager: The storage manager instance
    """
    from settings import MAX_MESSAGE_LENGTH
    
    if not should_respond_to_message(message):
        return
    
    try:
        async with message.channel.typing():
            print(f"FROM: {message.author.name}: {message.content}")
            
            # Process attachments
            attachments, success = await process_message_attachments(message)
            if not success:
                await message.channel.send("An error occurred while processing your attachments.")
                return
            
            if message.attachments and len(attachments) == 0:
                await message.channel.send("Attachments are of unsupported file types.")
                return
            
            # Construct query
            query = await construct_query(message, attachments)
            
            # Generate response
            response_text = ai_service.generate_response(
                message.channel.id,
                attachments,
                query
            )
            
            # Send response
            await split_and_send_messages(message, response_text, MAX_MESSAGE_LENGTH)
            
            # Save to persistent storage
            storage_manager.save_chat_history(
                message.channel.id,
                ai_service.get_history(message.channel.id)
            )
            
    except Exception as e:
        print(f"Error: {e}")
        print(traceback.format_exc())
        
        # Handle specific error codes
        if hasattr(e, 'code') and getattr(e, 'code', None) == 50035:
            await message.channel.send("The message is too long for me to process.")
        else:
            await message.channel.send("An error occurred while processing your message.")
