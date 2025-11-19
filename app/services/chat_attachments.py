from sqlalchemy.orm import Session
from app.models.db_models import ChatAttachments
from app.utils.logger import logger
from typing import List, Dict, Any, Optional


class ChatAttachmentsService:
    """Service for managing chat attachments"""
    
    @staticmethod
    def save_attachments(
        db: Session,
        chat_session_id: str,
        message_id: str,
        user_id: str,
        attachments: List[Dict[str, Any]]
    ) -> List[ChatAttachments]:
        """
        Save multiple attachments for a chat message
        
        Args:
            db: Database session
            chat_session_id: Chat session ID
            message_id: Message ID (event_id)
            user_id: User ID
            attachments: List of attachment dictionaries containing s3_url, file_name, etc.
            
        Returns:
            List of created ChatAttachments objects
        """
        saved_attachments = []
        
        try:
            for attachment in attachments:
                chat_attachment = ChatAttachments(
                    chat_session_id=chat_session_id,
                    message_id=message_id,
                    user_id=user_id,
                    s3_url=attachment.get('s3_url'),
                    file_name=attachment.get('file_name'),
                    file_type=attachment.get('file_type'),
                    file_size=attachment.get('file_size')
                )
                
                db.add(chat_attachment)
                saved_attachments.append(chat_attachment)
            
            db.commit()
            logger.info(f"Saved {len(saved_attachments)} attachments for message {message_id}")
            return saved_attachments
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving attachments for message {message_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_attachments_by_message(
        db: Session,
        chat_session_id: str,
        message_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all attachments for a specific message
        
        Args:
            db: Database session
            chat_session_id: Chat session ID
            message_id: Message ID (event_id)
            user_id: User ID
            
        Returns:
            List of attachment dictionaries
        """
        try:
            attachments = db.query(ChatAttachments).filter(
                ChatAttachments.chat_session_id == chat_session_id,
                ChatAttachments.message_id == message_id,
                ChatAttachments.user_id == user_id
            ).all()
            
            return [
                {
                    "id": attachment.id,
                    "s3_url": attachment.s3_url,
                    "file_name": attachment.file_name,
                    "file_type": attachment.file_type,
                    "file_size": attachment.file_size,
                    "created_at": attachment.created_at.isoformat() if attachment.created_at else None
                }
                for attachment in attachments
            ]
            
        except Exception as e:
            logger.error(f"Error getting attachments for message {message_id}: {str(e)}")
            return []
    
    @staticmethod
    def get_attachments_by_session(
        db: Session,
        chat_session_id: str,
        user_id: str
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all attachments for a chat session grouped by message_id
        
        Args:
            db: Database session
            chat_session_id: Chat session ID
            user_id: User ID
            
        Returns:
            Dictionary with message_id as key and list of attachments as value
        """
        try:
            attachments = db.query(ChatAttachments).filter(
                ChatAttachments.chat_session_id == chat_session_id,
                ChatAttachments.user_id == user_id
            ).all()
            
            grouped_attachments = {}
            for attachment in attachments:
                message_id = attachment.message_id
                if message_id not in grouped_attachments:
                    grouped_attachments[message_id] = []
                
                grouped_attachments[message_id].append({
                    "id": attachment.id,
                    "s3_url": attachment.s3_url,
                    "file_name": attachment.file_name,
                    "file_type": attachment.file_type,
                    "file_size": attachment.file_size,
                    "created_at": attachment.created_at.isoformat() if attachment.created_at else None
                })
            
            return grouped_attachments
            
        except Exception as e:
            logger.error(f"Error getting attachments for session {chat_session_id}: {str(e)}")
            return {}
    


# Create a singleton instance
chat_attachments_service = ChatAttachmentsService() 