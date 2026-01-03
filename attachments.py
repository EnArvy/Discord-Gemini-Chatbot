"""
Handles downloading and processing Discord attachments.
Determines MIME types and prepares attachments for AI processing.
"""
import aiohttp
from typing import List, Dict, Optional
from discord import Attachment


# Mapping of file extensions to MIME types
MIME_TYPE_MAPPING = {
    'image': ['.png', '.jpeg', '.jpg', '.heic', '.webp', '.heif'],
    'audio': ['.wav', '.mp3', '.aiff', '.aac', '.ogg', '.flac'],
    'text': ['.html', '.css', '.md', '.csv', '.xml', '.rtf'],
    'application': {
        '.pdf': 'application/pdf',
        '.js': 'application/x-javascript',
        '.py': 'application/x-python',
    }
}


def _get_mime_type(filename: str) -> Optional[str]:
    """
    Determine the MIME type based on file extension.
    
    Args:
        filename: The name of the file
        
    Returns:
        The MIME type string or None if unsupported
    """
    filename_lower = filename.lower()
    ext = f".{filename_lower.split('.')[-1]}"
    
    # Check image types
    if ext in MIME_TYPE_MAPPING['image']:
        return f"image/{ext[1:]}"
    
    # Check audio types
    if ext in MIME_TYPE_MAPPING['audio']:
        return f"audio/{ext[1:]}"
    
    # Check text types
    if ext in MIME_TYPE_MAPPING['text']:
        return f"text/{ext[1:]}"
    
    # Check application types
    if ext in MIME_TYPE_MAPPING['application']:
        return MIME_TYPE_MAPPING['application'][ext]
    
    return None


async def get_attachment_data(attachments: List[Attachment]) -> Optional[List[Dict[str, bytes]]]:
    """
    Download and process attachments from Discord.
    
    Args:
        attachments: List of Discord attachments
        
    Returns:
        List of dictionaries with 'mime_type' and 'data' keys, or None if error
    """
    result = []
    
    for attachment in attachments:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as resp:
                    if resp.status != 200:
                        return None
                    
                    attachment_data = await resp.read()
                    mime_type = _get_mime_type(attachment.filename)
                    
                    if mime_type:
                        result.append({
                            "mime_type": mime_type,
                            "data": attachment_data
                        })
        except Exception:
            return None
    
    return result
