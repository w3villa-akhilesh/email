import requests
from fastapi import APIRouter, HTTPException, Query, Depends, Header
from fastapi.responses import JSONResponse, HTMLResponse
from requests_oauthlib import OAuth2Session
from sqlalchemy.orm import Session
from typing import Optional

from database.connection import get_db
from services.user_service import insert_user as service_insert_user
from config import config
from logger import logger

router = APIRouter(tags=["authentication"])

# Initialize OAuth2 session (outside of functions to reuse)
oauth = OAuth2Session(
    config.KIVO_CLIENT_ID, 
    redirect_uri=config.KIVO_CALLBACK_URL, 
    scope=config.KIVO_SCOPE
)

# Dependency to extract the token from the Authorization header
def get_token(authorization: str = Header(..., description="Kivo access token for authorization")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Invalid token format")
    token = authorization[len("Bearer "):]
    return token

# Function to validate token with Kivo provider
def validate_token(access_token: str):
    """
    Validates the access token with Kivo provider.
    Raises HTTPException if token is invalid.
    """
    validation_url = f"{config.KIVO_PROVIDER_URL}/api/v1/users/me.json"
    try:
        validation_response = requests.get(
            validation_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        validation_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Token validation failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid or expired access token")

@router.get('/kivo-sign-in')
async def kivo_sign_in():
    """
    Generates the authorization URL for Kivo OAuth.
    """
    authorization_url = f'{config.KIVO_PROVIDER_URL}{config.KIVO_AUTHORIZE_PATH}?response_type=code&client_id={config.KIVO_CLIENT_ID}&redirect_uri={config.KIVO_CALLBACK_URL}&scope={config.KIVO_SCOPE}'
    return JSONResponse(content={"authorization_url": authorization_url})

@router.get("/verify")
async def verify(code: str = Query(...), db: Session = Depends(get_db)):
    """
    Verifies the user after OAuth authorization, exchanges code for tokens,
    fetches user info, and inserts/updates user in the database.
    """
    try:
        logger.info("Exchanging authorization code for access token...")
        # Exchange authorization code for an access token
        token_url = f"{config.KIVO_PROVIDER_URL}/oauth/token"
        token_response = requests.post(token_url, data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": config.KIVO_CALLBACK_URL,
            "client_id": config.KIVO_CLIENT_ID,
            "client_secret": config.KIVO_CLIENT_SECRET
        })
        token_response.raise_for_status()
        token_data = token_response.json()

        logger.info(f"Token received: {token_data}")

        # Fetch user info from Kivo API
        user_info_url = f"{config.KIVO_PROVIDER_URL}/api/v1/users/me.json"
        user_response = requests.get(user_info_url, headers={
            "Authorization": f"Bearer {token_data['access_token']}"
        })
        user_response.raise_for_status()
        raw_info = user_response.json()

        logger.info(f"User info fetched: {raw_info}")

        # Extract user information
        kivo_id = str(raw_info["current_profile"]["id"])

        # Check if the user is an admin
        is_admin = raw_info["current_profile"].get("is_admin", False)
        if not is_admin:
            return JSONResponse(
                content={"error": "You are not authorized to log in. Admin access is required."},
                status_code=403
            )

        # Prepare user data for insertion
        kivo_user_data = {
            "kivo_id": kivo_id,
            "firstName": raw_info["current_profile"]["first_name"],
            # "dp_url_small": raw_info["current_profile"]["profile_pic_url"],
            "email": raw_info["current_profile"]["email"],
            "timeZone": raw_info["current_profile"]["time_zone"],
            "refresh_token": token_data["refresh_token"],
            "access_token": token_data["access_token"]
        }

        # Insert the data into the database using the SQLAlchemy service
        insert_result = service_insert_user(db, kivo_user_data)

        # Handle insert result
        if insert_result == "User data inserted successfully" or insert_result == "User data already exists":
            # Return success HTML page
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Authorization Successful</title>
            </head>
            <body>
               <div>
                    <h1>Authorization Successful!</h1>
                    <p>Welcome, {raw_info["current_profile"]["first_name"]}! You have been successfully authenticated.</p>
                    <p>Redirecting you to the dashboard...</p>
                    <script>
                        localStorage.setItem('access_token', '{token_data["access_token"]}');
                        window.location.href = '{config.ADMIN_DASHBOARD_URL}/dashboard?access_token=' + localStorage.getItem('access_token');
                     </script>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content)
        else:
            raise HTTPException(status_code=500, detail=insert_result)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error during token exchange or user info fetching: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch user information from Kivo API")
    except KeyError as e:
        logger.error(f"Missing key in response: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Missing key in Kivo API response: {e}. Please check Kivo API documentation.")

@router.get("/user")
async def fetch_user_data(access_token: str, db: Session = Depends(get_db)):
    """
    Fetches detailed user information from Kivo API using the provided access token.
    """
    try:
        user_info_url = f"{config.KIVO_PROVIDER_URL}/api/v1/users/me.json"

        user_response = requests.get(user_info_url, headers={
            "Authorization": f"Bearer {access_token}"
        })
        user_response.raise_for_status()
        user_data = user_response.json()

        user_info = {
            "kivo_id": str(user_data["current_profile"]["id"]),
            "first_name": user_data["current_profile"]["first_name"],
            "last_name": user_data["current_profile"].get("last_name", ""), # Use .get for optional fields
            "email": user_data["current_profile"]["email"],
            # "profile_pic_url": user_data["current_profile"].get("profile_pic_url", ""), # Use .get for optional fields
            "time_zone": user_data["current_profile"].get("time_zone", ""), # Use .get for optional fields
            "is_admin": user_data["current_profile"].get("is_admin", False),
            "access_token": access_token
        }

        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": "User data fetched successfully", "data": user_info}
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching user data from Kivo API: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user information from Kivo API. Check access token validity.")
    except KeyError as e:
        logger.error(f"Missing key in Kivo API response for /user endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Missing key in Kivo API response: {e}. Please check Kivo API documentation.")

# Export the validate_token and get_token functions for use in other routers
__all__ = ['router', 'validate_token', 'get_token']
