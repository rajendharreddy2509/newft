import uvicorn
from app import app  # Import the app from the app module

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
