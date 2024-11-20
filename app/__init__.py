from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.user_settings.broker_integration import router as broker_integration_router

# Create FastAPI instance
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # List of allowed origins
    allow_credentials=True,  # Allow cookies to be sent along with the request
    allow_methods=["*"],     # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],     # Allow all headers
)

# Include the broker integration router
app.include_router(broker_integration_router, prefix="/api/broker", tags=["broker"])

# Other includes, middleware, and configurations can go here
