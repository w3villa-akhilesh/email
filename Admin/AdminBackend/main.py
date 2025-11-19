from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.connection import engine, Base
from config import config
from logger import logger

# Import routers
from routers.auth import router as auth_router
from routers.events import router as events_router
from routers.dashboard import router as dashboard_router
from routers.companies import router as companies_router
from routers.agents import router as agents_router
from routers.llm_credentials_new import router as llm_credential_router, router_plural as llm_credentials_router
from routers.agent_mappings import router as agent_mappings_router
from routers.agent_keys import router as agent_keys_router
from routers.network_activity_logs import router as network_activity_logs_router
from adk_adapter import register_adk_routes

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully (if they didn't exist).")
    yield
    # Shutdown (if needed)
    pass

app = FastAPI(lifespan=lifespan)

# Allow CORS for your frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(auth_router)
app.include_router(events_router)
app.include_router(dashboard_router)
app.include_router(companies_router)
app.include_router(agents_router)
app.include_router(llm_credential_router)
app.include_router(llm_credentials_router)  # Plural endpoint for backward compatibility
app.include_router(agent_mappings_router)
app.include_router(agent_keys_router)
app.include_router(network_activity_logs_router)


# Register ADK-compatible routes for use with Google ADK Web UI
register_adk_routes(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.APP_HOST, port=config.APP_PORT, reload=config.DEBUG)
