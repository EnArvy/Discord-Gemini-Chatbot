"""
Persistence layer for storing and retrieving conversation history and tracked threads.
"""
import shelve
from typing import Dict, List


class ChatDataManager:
    """Manages persistent storage of chat history and tracked threads."""
    
    DB_NAME = 'chatdata'
    
    @staticmethod
    def load_chat_history() -> Dict[int, List]:
        """Load chat history from persistent storage."""
        history = {}
        with shelve.open(ChatDataManager.DB_NAME) as db:
            for key in db.keys():
                if key.isnumeric():
                    history[int(key)] = db[key]
        return history
    
    @staticmethod
    def load_tracked_threads() -> List[int]:
        """Load list of tracked threads from persistent storage."""
        with shelve.open(ChatDataManager.DB_NAME) as db:
            if 'tracked_threads' in db:
                return db['tracked_threads']
        return []
    
    @staticmethod
    def save_chat_history(channel_id: int, history: List) -> None:
        """Save chat history for a specific channel."""
        with shelve.open(ChatDataManager.DB_NAME) as db:
            db[str(channel_id)] = history
    
    @staticmethod
    def save_tracked_threads(threads: List[int]) -> None:
        """Save list of tracked threads."""
        with shelve.open(ChatDataManager.DB_NAME) as db:
            db['tracked_threads'] = threads
    
    @staticmethod
    def delete_chat_history(channel_id: int) -> None:
        """Delete chat history for a specific channel."""
        with shelve.open(ChatDataManager.DB_NAME) as db:
            key = str(channel_id)
            if key in db:
                del db[key]


def log_error(text: str, error_traceback: str, history: str, 
              candidates: str, parts: str, prompt_feedbacks: str) -> None:
    """Log errors to file for debugging."""
    with open('errors.log', 'a+', encoding='utf-8') as errorlog:
        errorlog.write('\n##########################\n')
        errorlog.write('Message: ' + text)
        errorlog.write('\n-------------------\n')
        errorlog.write('Traceback:\n' + error_traceback)
        errorlog.write('\n-------------------\n')
        errorlog.write(f'History:\n{history}')
        errorlog.write('\n-------------------\n')
        errorlog.write('Candidates:\n' + str(candidates))
        errorlog.write('\n-------------------\n')
        errorlog.write('Parts:\n' + str(parts))
        errorlog.write('\n-------------------\n')
        errorlog.write('Prompt feedbacks:\n' + str(prompt_feedbacks))
