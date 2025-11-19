from app.utils.logger import logger
from app.models.db_models import MatchingNotification, UserSession
from app.services.my_sql_client import get_db
from sqlalchemy.orm import Session
from sqlalchemy import or_

async def handle_fetch_all_notifications(user_id, page: int = 1, page_size: int = 10, app_name: str = None):
    """
    Fetch all notifications with pagination. Newest notifications are returned first.
    If app_name is provided, the notifications will be filtered by the app_name.
    """
    logger.info("invoking handle_fetch_all_notifications method")
    db: Session = next(get_db())

    try:
        query = (
            db.query(MatchingNotification, UserSession)
            .join(UserSession, MatchingNotification.session_id == UserSession.session_id)
            .filter(
                UserSession.user_id == user_id,
                MatchingNotification.is_clear == False
            )
        )
        if app_name:
            query = query.filter(
                or_(
                    UserSession.app_name == app_name,
                    UserSession.app_name == None,
                    UserSession.app_name == ''
                )
            )
        all_notifications = (
            query
            .order_by(MatchingNotification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        results = []
        for n, session in all_notifications:
            results.append({
                "message_id": n.custom_matching_id,
                "session_id": n.session_id,
                "message": n.message,
                "is_read": n.is_read,
                "is_clear": n.is_clear,
                "created_at": n.created_at.isoformat(),
                "last_summary": session.last_summary if session else None
            })
        return results
    except Exception as e:
        logger.error(f"Error fetching unread notifications: {e}", exc_info=True)
        return []


async def mark_notification_as_read(message_id: str):
    logger.info("invoking mark_notification_as_read method")
    db: Session = next(get_db())
    try: 
        notification = db.query(MatchingNotification).filter(MatchingNotification.custom_matching_id == message_id).first()
        if notification:
            notification.is_read = True
            db.commit()
            return {"status": "success", "message": f"Notification marked as read for message_id {message_id}."}
        else:
            return {"status": "error", "message": "Notification not found."}
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}", exc_info=True)
        return {"status": "error", "message": "Failed to mark notification as read."}
    

async def mark_all_notifications_as_read(app_name: str = None):
    logger.info("invoking mark_all_notification_as_read method")
    db: Session = next(get_db())
    try: 
        query = db.query(MatchingNotification)
        if app_name:
            query = query.join(UserSession, MatchingNotification.session_id == UserSession.session_id).filter(
                or_(
                    UserSession.app_name == app_name,
                    UserSession.app_name == None,
                    UserSession.app_name == ''
                )
            )
        notifications = query.filter(MatchingNotification.is_read == False).all()
        if notifications:
            for notification in notifications:
                notification.is_read = True
            db.commit()
            return {"status": "success", "message": f"All Notifications marked as read."}
        else:
            return {"status": "info", "message": "unread notifications not found."}
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}", exc_info=True)
        return {"status": "error", "message": "Failed to mark all notifications as read."}

async def clear_all_notification(app_name: str = None):
    logger.info("invoking clear_all_notification")
    db: Session = next(get_db())
    try:
        query = db.query(MatchingNotification)
        if app_name:
            query = query.join(UserSession, MatchingNotification.session_id == UserSession.session_id).filter(
                or_(
                    UserSession.app_name == app_name,
                    UserSession.app_name == None,
                    UserSession.app_name == ''
                )
            )
        query.update({MatchingNotification.is_clear: True})
        db.commit()
        return {"status": "success", "message": "All notifications cleared."}
    except Exception as e:
        logger.error(f"Error clearing all notifications: {e}", exc_info=True)
        return {"status": "error", "message": "Failed to clear notifications."}
