"""
COVENANT.AI API Server
Main FastAPI application for the Constitutional AI framework.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="COVENANT.AI",
    description="Constitutional Alignment Framework for Autonomous Intelligence",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
try:
    from covenant.api.routes import router
    app.include_router(router, prefix="/api/v1")
    logger.info("API routes loaded successfully")
except ImportError as e:
    logger.warning(f"Could not load routes: {e}")

@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "name": "COVENANT.AI",
        "version": "2.0.0",
        "status": "operational",
        "description": "Constitutional Alignment Framework for Autonomous Intelligence"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the API server."""
    logger.info(f"Starting COVENANT.AI server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run_server()
