# config.py

from pydantic_settings import BaseSettings
from typing import Dict, Optional
from SmartApi import SmartConnect

class Settings(BaseSettings):
    db_user: str
    db_password: str
    db_host: str
    db_name: str
    db_port: int

    MAIL_SERVER: str = 'smtp.gmail.com'  # Added type annotation
    MAIL_PORT: int = 587  # Added type annotation
    MAIL_USE_TLS: bool = True  # Added type annotation
    MAIL_USERNAME: str = 'saich5252@gmail.com'  # Added type annotation
    MAIL_PASSWORD: str = 'vfdesgvzxpbpnsko'  # Added type annotation
    MAIL_FROM: str = 'saich5252@gmail.com'
    MAIL_USE_TLS: bool = True  # Use TLS for secure email sending
    MAIL_STARTTLS: bool = True  # Use STARTTLS for email
    MAIL_SSL_TLS: bool = False
    CLIENT_CODE: str = ""  # Added type annotation
    PASSWORD: str = ""  # Added type annotation
    API_KEY: str = ""  # Added type annotation
    TOKEN: str = ""  # Added type annotation
    AUTH_TOKEN: Optional[str] = None  # Optional type annotation
    FEED_TOKEN: Optional[str] = None  # Optional type annotation

    class Config:
        env_file = ".env"

# Instantiate settings
settings = Settings()

# Session management dictionaries
SMART_API_OBJ_angelone: Dict[str, SmartConnect] = {}  # Stores SmartConnect objects for each user
angel_one_data: Dict[str, dict] = {}  # Stores session data for each user

# Any additional setup or configuration can be added as needed, such as API endpoint URLs, logging configurations, etc.
