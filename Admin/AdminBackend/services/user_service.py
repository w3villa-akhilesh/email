from sqlalchemy.orm import Session
from database.models import User
from sqlalchemy.exc import SQLAlchemyError
from logger import logger

def insert_user(db: Session, kivo_user_data: dict):
    try:
        existing_user = db.query(User).filter(User.kivo_id == kivo_user_data["kivo_id"]).first()

        if existing_user:
            logger.info(f"User with kivo_id {kivo_user_data['kivo_id']} already exists.")
            return "User data already exists"

        new_user = User(
            kivo_id=kivo_user_data["kivo_id"],
            firstName=kivo_user_data["firstName"],
            # dp_url_small=kivo_user_data["dp_url_small"],
            email=kivo_user_data["email"],
            timeZone=kivo_user_data["timeZone"],
            refresh_token=kivo_user_data["refresh_token"],
            access_token=kivo_user_data["access_token"]
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info(f"User data for {kivo_user_data['firstName']} inserted successfully.")
        return "User data inserted successfully"

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error while inserting user data: {e}")
        return "Failed to insert user data"

def fetch_all_users(db: Session):
    """
    Fetches all users from the database.

    Args:
        db: The SQLAlchemy session.

    Returns:
        A list of User objects if successful, or an error message string.
    """
    try:
        users = db.query(User).all()
        if not users:
            logger.info("No users found in the database.")
            return [] # Return an empty list if no users are found
        return users
    except SQLAlchemyError as e:
        logger.error(f"Error while fetching all users: {e}")
        return "Failed to fetch users"