# app/api/brokers/angelone.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from SmartApi import SmartConnect
import pyotp
from logzero import logger
import config  # Assuming config has necessary variables like SMART_API_OBJ_angelone

router = APIRouter()

class AngelOneLoginRequest(BaseModel):
    userId: str
    password: str
    apiKey: str
    qrCode: str

async def execute(data: AngelOneLoginRequest):
    return await handle_angelone_validation(data)

async def handle_angelone_validation(data: AngelOneLoginRequest):
    userName = data.userId
    pswrd = data.password
    apikey = data.apiKey
    qrcode = data.qrCode

    if not all([userName, pswrd, apikey, qrcode]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    try:
        totp = pyotp.TOTP(qrcode).now()
    except Exception as e:
        logger.error("Invalid QR Code for user %s: %s", userName, str(e))
        raise HTTPException(status_code=500, detail=f"Invalid QR Code for user {userName}. Error: {str(e)}")

    obj = config.SMART_API_OBJ_angelone.get(userName) or SmartConnect(api_key=apikey)
    if userName not in config.SMART_API_OBJ_angelone:
        config.SMART_API_OBJ_angelone[userName] = obj

    try:
        session_data = obj.generateSession(userName, pswrd, totp)
        
        if not isinstance(session_data, dict) or not session_data.get("status", False):
            error_message = session_data.get("message", "Unknown error").replace("Invalid totp", "Invalid QR Code or User ID")
            raise HTTPException(status_code=400, detail=error_message)

        config.angel_one_data[userName] = session_data
        refreshToken = session_data['data'].get('refreshToken')
        auth_token = session_data['data'].get('jwtToken')
        feedToken = obj.getfeedToken()

        userProfile = obj.getProfile(refreshToken)
        balance = obj.rmsLimit()
        userProfile['data']['availablecash'] = float(balance['data']['availablecash'])
        userProfile['data']['Net'] = float(balance['data']['net'])

        config.AUTH_TOKEN = auth_token
        config.FEED_TOKEN = feedToken

        return {"message": f"Validation Successful: {userName}", "data": userProfile}
    except Exception as e:
        logger.error("Error validating account for user %s: %s", userName, str(e))
        raise HTTPException(status_code=500, detail=f"Error validating account for user {userName}. Error: {str(e)}")
