"""
SkyLark Business Intelligence AI Agent
FastAPI Backend Application

This is the main entry point for the FastAPI application.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import get_settings
from .routers import ask_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Runs on startup and shutdown.
    """
    # Startup
    settings = get_settings()
    logger.info(f"Starting {settings.APP_NAME}...")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"Deals Board ID: {settings.DEALS_BOARD_ID}")
    logger.info(f"Work Orders Board ID: {settings.WORK_ORDERS_BOARD_ID}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    settings = get_settings()
    
    app = FastAPI(
        title=settings.APP_NAME,
        description="Business Intelligence AI Agent for monday.com integration. "
                    "Provides founder-level insights from Deals and Work Orders data.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    # Configure CORS for React frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(ask_router, tags=["Business Intelligence"])
    
    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """Root endpoint with API information."""
        return {
            "name": settings.APP_NAME,
            "version": "1.0.0",
            "description": "Business Intelligence AI Agent for monday.com",
            "docs": "/docs",
            "health": "/health"
        }
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
                "code": "INTERNAL_ERROR"
            }
        )
    
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
