import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from sqladmin import Admin
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
import sqladmin

# Import local modules
from database import engine, check_database_connection, create_tables
from models import (
    User, Event, LLMCredentials, SessionMode, ChatAttachment, 
    CompanyIntegrationConfig, EmailInboxConfig, IATSUserSession, 
    IATSLLMCredentials, Session
)
from admin_views import admin_views
from config import settings

# Lifespan function for startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("\n🚀 Starting Kivo Admin Panel...")
    print("=" * 50)
    
    # Validate configuration
    if not settings.validate_required_settings():
        print("❌ Configuration validation failed!")
        yield
        return
    
    # Check database connection
    if not check_database_connection():
        print("❌ Database connection failed!")
        yield
        return
    
    # Create tables
    if not create_tables():
        print("❌ Table creation failed!")
        yield
        return
    
    print("✅ Database tables created/verified successfully!")
    print(f"🌐 Admin panel available at: http://{settings.HOST}:{settings.PORT}/admin")
    print(f"👤 Default login - Username: {settings.ADMIN_USERNAME}")
    print(f"🔑 Password: {settings.ADMIN_PASSWORD}")
    print("=" * 50)
    
    yield
    
    # Shutdown
    print("👋 Shutting down Kivo Admin Panel...")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Kivo Admin Panel",
    description="Beautiful Admin UI for Kivo Agent Management",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Add session middleware for authentication
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# Mount SQLAdmin static files (CSS, JavaScript, fonts)
# This ensures the admin panel's UI assets are properly served
sqladmin_static_path = os.path.join(os.path.dirname(sqladmin.__file__), "statics")
app.mount("/admin/statics", StaticFiles(directory=sqladmin_static_path), name="admin_static")

# Simple authentication backend for SQLAdmin
class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username, password = form["username"], form["password"]
        
        if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
            # Store user info in session
            request.session.update({"token": "authenticated", "user": username})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        return token == "authenticated"

# Initialize SQLAdmin
authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)
admin = Admin(
    app, 
    engine, 
    authentication_backend=authentication_backend,
    title="Kivo Admin Panel",
    logo_url=None,  # You can add a logo URL here
)

# Add all admin views
for view_class in admin_views:
    admin.add_view(view_class)

# Health check endpoints
@app.get("/")
async def root():
    return {
        "message": "Kivo Admin Panel is running!",
        "admin_url": "/admin",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    db_status = check_database_connection()
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected",
        "admin_panel": "available at /admin"
    }

# Startup and shutdown logic is now handled in the lifespan function above

if __name__ == "__main__":
    # Validate settings before starting
    if settings.validate_required_settings():
        uvicorn.run(
            "main:app", 
            host=settings.HOST, 
            port=settings.PORT, 
            reload=settings.DEBUG,
            reload_dirs=["."] if settings.DEBUG else None,
            log_level=settings.LOG_LEVEL.lower()
        )
    else:
        print("\n❌ Cannot start server due to configuration errors")
        print("Please check your environment variables or .env file")
