import os
import json
import random
from base64 import urlsafe_b64encode, urlsafe_b64decode
from pydantic import BaseModel, constr, validator
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet, InvalidToken
from app.models.user import User, BrokerCredentials,StrategyMultipliers, Strategies
from app.database.connection import get_db
from config import settings
import importlib.util
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.api.brokers.angelone import AngelOneLoginRequest
from .router import USERSETTING_ROUTES
from .errorHandling import ERROR_HANDLER
from fastapi import Request

# FastAPI mail configuration
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True
)
mail = FastMail(conf)

def generate_6otp():
    return ''.join(random.choices("0123456789", k=6))

def validate_request_data(data):
    required_fields = ['mainUser', 'userId', 'password', 'apiKey', 'qrCode', 'broker', 'display_name', 'max_profit', 'max_loss']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValueError(f'Missing required fields: {", ".join(missing_fields)}')

key_file_path = 'fernet_key.json'
if os.path.exists(key_file_path):
    with open(key_file_path, 'r') as key_file:
        key_data = json.load(key_file)
        fernet_key = key_data['fernet_key']
else:
    fernet_key = Fernet.generate_key()
    with open(key_file_path, 'w') as key_file:
        json.dump({'fernet_key': fernet_key.decode()}, key_file)

cipher_suite = Fernet(fernet_key)

def encrypt_data(data):
    return urlsafe_b64encode(cipher_suite.encrypt(data.encode()))

def decrypt_data(encrypted_data):
    try:
        return cipher_suite.decrypt(urlsafe_b64decode(encrypted_data)).decode()
    except InvalidToken:
        raise HTTPException(status_code=400, detail="Invalid encryption token")

class AccountValidationData(BaseModel):
    mainUser: str
    userId: str
    password: str
    apiKey: str
    qrCode: str
    broker: str
    display_name: str
    max_profit: int
    max_loss: int
    secretKey: str = None
    imei: str = None
    vendor_code: str = None
    client_id: str = None
    
class BrokerIntegration:
    async def account_validation(self, data: AccountValidationData, db: Session = Depends(get_db)):
        try:
            print("Received data:", data)
            validate_request_data(data.dict())

            broker = data.broker
            username = data.mainUser

            # if not existing_user:
            #     raise HTTPException(status_code=404, detail="User not found.")

            if broker == "pseudo_account":
                print('pseudo entered')
                existing_user = db.query(User).filter(User.username == username).first()
                if not existing_user:
                    raise HTTPException(status_code=404, detail="User not found.")
                
                existing_account = db.query(BrokerCredentials).filter_by(user_id=existing_user.id, 
                                                                         broker="pseudo_account", 
                                                                         broker_user_id=data.userId).first()
                if existing_account:
                    print("existing account : ",existing_account)
                    available_balance = existing_account.available_balance
                else:
                    available_balance = 1000000.00  # Default balance
                    pseudo_credentials = BrokerCredentials(
                        user_id=existing_user.id,
                        username=existing_user.username,
                        broker="pseudo_account",
                        display_name=data.display_name,
                        broker_user_id=data.userId,
                        max_profit=float(data.max_profit),  # Convert to float
                        max_loss=float(data.max_loss),       # Convert to float
                        profit_locking=",,,,",
                        available_balance=available_balance,
                        enabled=True
                    )
                    db.add(pseudo_credentials)
                    # db.flush()  # Optional: Ensure the ID is generated
                    db.commit()

                return JSONResponse(content={
                    'message': f'Validation Successful: {username}',
                    'data': {"name": "pseudo", "available_balance": available_balance}
                })
            existing_record = db.query(BrokerCredentials).filter_by(broker_user_id=data.userId).first()
            print("existing_record : ",existing_record)
            module_path = f"./app/api/brokers/{broker}.py"
            
            if existing_record:
                if broker == "angelone":
                    existing_record.enabled = True
                    db.commit()
                    angel_one_data = AngelOneLoginRequest(
                        mainUser=data.mainUser,
                        userId=data.userId,
                        password=data.password,
                        apiKey=data.apiKey,
                        qrCode=data.qrCode,
                    )
                    spec = importlib.util.spec_from_file_location(broker, module_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    response = await module.execute(angel_one_data)
                    response = JSONResponse(content=response, status_code=200)
                
                else:
                    raise HTTPException(status_code=400, detail=f"Broker {broker} is not supported.")
                if response:
                    # Update any necessary information in the existing record
                    existing_record.broker = broker
                    existing_record.display_name = data.display_name
                    existing_record.max_profit = float(data.max_profit)
                    existing_record.max_loss = float(data.max_loss)
                    db.commit()
                return response
            if broker == 'angelone':
                print('angelone entered')
                angel_one_data = AngelOneLoginRequest(
                        mainUser=data.mainUser,
                        userId=data.userId,
                        password=data.password,
                        apiKey=data.apiKey,
                        qrCode=data.qrCode,
                    )
                spec = importlib.util.spec_from_file_location(broker, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                response = await module.execute(angel_one_data)
                response = JSONResponse(content=response, status_code=200)
                print("angel done", response)
            else:
                raise HTTPException(status_code=400, detail=f"Broker {broker} is not supported.")
            try:
                response_code = response.status_code
            except:
                response_code = response.status_code
            print(response_code)
            if response_code == 200 or response_code == '200 OK':
                user = db.query(User).filter(User.username == username).first()
                if not user:
                    raise HTTPException(status_code=404, detail="User not found.")
                print("user : ",user,"\n\n\n\n")
                # current_broker_count = len([
                #     bc for bc in user.broker_credentials if bc.broker != 'pseudo_account'
                # ])
                # # Check subscription limits
                # if user.num_of_users ==0:
                #     return JSONResponse({"message": "Subscription Expired.Renew your Subscription Plan"}), 403
                
                # elif user.is_on_trial and current_broker_count >= user.num_of_users:
                #     return JSONResponse({"message": "Your trial subscription plan does not allow adding more broker accounts."}), 403
                # elif not user.is_on_trial and current_broker_count >= user.num_of_users:
                #     return JSONResponse({"message": "You have reached the limit for adding Deemat accounts on your current plan."}), 403
    
                if user:
                    encrypted_password = encrypt_data(data.password)
                    encrypted_api_key = encrypt_data(data.apiKey) if data.apiKey else None
                    encrypted_qr_code = encrypt_data(data.qrCode)
                    encrypted_secret_key = encrypt_data(data.secretKey) if data.secretKey else None
                    encrypted_imei = encrypt_data(data.imei) if data.imei else None
                    print(response)
                    broker_credentials = BrokerCredentials(
                        user=user,
                        username=username,
                        broker=broker,
                        broker_user_id = data.userId,
                        display_name = data.display_name,
                        max_profit = data.max_profit,
                        max_loss = data.max_loss,
                        client_id = data.client_id if data.client_id in data else None,
                        vendor_code = data.vendor_code if data.vendor_code in data else None,
                        # redirect_url = data['REDIRECT_URI'] if 'REDIRECT_URI' in data else None,
                        password=encrypted_password.decode(),
                        api_key=encrypted_api_key.decode() if encrypted_api_key else None,
                        qr_code=encrypted_qr_code.decode(),
                        secret_key=encrypted_secret_key.decode() if encrypted_secret_key else None,
                        imei=encrypted_imei.decode() if encrypted_imei else None,
                        enabled = True
                    )
                    db.add(broker_credentials)
                    db.commit()
                    
            return response
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error in validation: {str(e)}")

    def get_startegy_account(self, username, db: Session = Depends(get_db)):
        try:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                response_data = ERROR_HANDLER.database_errors("user", "User not found.")
                return JSONResponse(content=response_data, status_code=404)
            enabled_credentials = db.query(BrokerCredentials).filter(
                BrokerCredentials.user_id == user.id,
                BrokerCredentials.enabled == True
            ).all()
            if not enabled_credentials:
                raise HTTPException(status_code=404, detail="No enabled broker credentials found.")
            response_data ={
                'message': 'Login successful',
                'data': []
            }
            for credential in enabled_credentials:
                multipliers = db.query(StrategyMultipliers).filter(
                    StrategyMultipliers.broker_user_id == credential.broker_user_id
                ).all()
                strategy_tags = {}
                for multiplier in multipliers:
                    strategy_tags[multiplier.strategy_id] = multiplier.multiplier
                response_data['data'].append({
                    'broker': credential.broker,
                    'broker_id': credential.broker_user_id,
                    'display_name': credential.display_name,
                    'Login enabled': credential.enabled,
                    'available balance': credential.available_balance,
                    'multipliers': strategy_tags
                })
            return response_data
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error in validation: {str(e)}")
    
    def delete_broker_account(self, username, broker_user_id,broker, db: Session = Depends(get_db)):
        try:
            print("entered the delete function", username, broker_user_id,broker)
            existing_record = db.query(BrokerCredentials).filter_by(broker_user_id=broker_user_id, username = username).first()
            print("existing_record : ",existing_record)
            if not existing_record:
                response_data = ERROR_HANDLER.database_errors("broker_credentials", 'Broker credentials not found')
                return JSONResponse(content=response_data, status_code=404)
            # try:
            #     pass
            #     related_strategies = db.query(Strategies).filter(
            #     Strategies.broker_user_id.contains(broker_user_id),
            #     Strategies.broker.contains(broker)
            #     ).all()
            #     for strategy in related_strategies:
            #         broker_user_ids = strategy.broker_user_id.split(',')
            #         brokers = strategy.broker.split(',')
            #         if ',' not in strategy.broker_user_id and ',' not in strategy.broker:
            #             # Strategy has a single broker_user_id and broker
            #             db.delete(strategy)
            #         else:
            #             # Strategy has multiple broker_user_ids and brokers
            #             broker_user_ids = [bid.strip() for bid in broker_user_ids if bid.strip() != broker_user_id.strip()]
            #             brokers = [br.strip() for br in brokers if br.strip() != broker.strip()]

            #             strategy.broker_user_id = ','.join(broker_user_ids)
            #             strategy.broker = ','.join(brokers)
            #         db.query(StrategyMultipliers).filter_by(strategy_id=strategy.id, broker_user_id=broker_user_id).delete()
            # except Exception as e:
            #     print(f"Error deleting strategy: {str(e)}")
            #     return JSONResponse(content=e, status_code=500)
            db.delete(existing_record)
            db.commit()
            response_data = {'message': 'Broker account deleted successfully'}
            return JSONResponse(content=response_data, status_code=200)
        except Exception as e:
            response_data = ERROR_HANDLER.database_errors("delete_broker_account", str(e))
            return JSONResponse(content=response_data, status_code=500)
    
    def update_password(self, username, broker_user_id,new_password, db: Session = Depends(get_db)):
        try:
            print('entered update')
            # new_password = password
            print(new_password)
            existing_record = db.query(BrokerCredentials).filter_by(broker_user_id=broker_user_id,username=username).first()
            print("existing_record : ",existing_record)
            if existing_record:
                encrypted_password = encrypt_data(new_password)
                existing_record.password = encrypted_password.decode()
                db.commit()
                response_data = {'message': 'Password updated successfully'}
                return JSONResponse(content=response_data, status_code=200)
        except ValueError as ve:
            response_data = ERROR_HANDLER.fastAPI_errors(str(ve))
            return JSONResponse(content=response_data, status_code=400)
        except Exception as e:
            response_data = ERROR_HANDLER.fastAPI_errors(str(e))
            return JSONResponse(content=response_data, status_code=500)
    
    def logout(self, username, broker_user_id, db: Session = Depends(get_db)):
        logout_account = db.query(BrokerCredentials).filter_by(broker_user_id=broker_user_id,username=username).first()

        if logout_account:
            logout_account.enabled = False
            db.commit()
            response_data = {'message': 'Logout successful'}
            return JSONResponse(content=response_data, status_code=200)
        else:
            response_data = ERROR_HANDLER.database_errors("broker_credentials", 'Invalid Details')
            return JSONResponse(content=response_data, status_code=400)
    
    def forget_password(self,username, db: Session = Depends(get_db)):
        application_user = db.query(User).filter_by(username=username).first()
        if application_user:
            otp = generate_6otp()
            application_user.otp = otp
            db.commit()
            msg = MessageSchema(
                subject="Account Verification",
                recipients=[application_user.email],
                # body=f"Your OTP for password reset is: {otp}",
                subtype="html"
            )
            msg.body = f'Hi { application_user.name },\n\n OTP for resetting your password { otp }.'
            fm = FastMail(conf)
            fm.send_message(msg)
            response_data = {'message': f'OTP generated successfully please check your email {application_user.email}'}
            return JSONResponse(content=response_data, status_code=200)
        else:
            response_data = ERROR_HANDLER.database_errors("user", 'User with email does not exist !')
            return JSONResponse(content=response_data, status_code=500)
    
    def verify_otp(self,username, request:Request, db: Session = Depends(get_db)):
        data = request.json()
        entered_otp = data.get('otp')
        application_user = db.query(User).filter_by(username=username).first()
        if application_user.otp == entered_otp:
            response_data = {'message': 'OTP verified successfully, Please change your Password !!'}
            return JSONResponse(content=response_data, status_code=200)
        else:
            response_data = ERROR_HANDLER.database_errors("user", 'Invalid OTP please verify again !!')
            return JSONResponse(content=response_data, status_code=400)
    def execcute_broker_integration(self, broker, username, db: Session = Depends(get_db)):
        try:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found.")
            return {"message": f"Broker integration executed for {username} with {broker}"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error in broker integration: {str(e)}")
       
router = APIRouter()

@router.post(USERSETTING_ROUTES.get_routes('validation'))
async def validate_account(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    user_data = data['users'][0]
    print("Incoming data:", user_data) 
    integration = BrokerIntegration()
    return await integration.account_validation(AccountValidationData(**user_data), db)
@router.get("/read")
async def execute_broker_integration(broker: str, username: str, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        return {"message": f"Broker integration executed for {username} with {broker}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in broker integration: {str(e)}")
    
# FastAPI Function for Deleting all the broker accounts
@router.delete(USERSETTING_ROUTES.get_routes('delete_broker_account'))
async def delete_broker_account(username: str, broker_user_id: str, broker: str, db: Session = Depends(get_db)):
    integration = BrokerIntegration()
    return integration.delete_broker_account(username, broker_user_id, broker, db)

@router.put(USERSETTING_ROUTES.get_routes('update_password'))
async def update_password(username: str, broker_user_id: str, password: str,  db: Session = Depends(get_db)):
    integration = BrokerIntegration()
    return integration.update_password(username, broker_user_id, password, db)

@router.post(USERSETTING_ROUTES.get_routes('logout'))
async def logout(username: str, broker_user_id: str, db: Session = Depends(get_db)):
    integration = BrokerIntegration()
    return integration.logout(username, broker_user_id, db)

@router.post(USERSETTING_ROUTES.get_routes('forgot_password'))
async def forget_password(username: str, db: Session = Depends(get_db)):
    integration = BrokerIntegration()
    return integration.forget_password(username, db)

@router.post(USERSETTING_ROUTES.get_routes('verify_otp'))
async def verify_otp(username: str, request: Request, db: Session = Depends(get_db)):
    integration = BrokerIntegration()
    return integration.verify_otp(username, request, db)

@router.post("/get_strategy_account/{username:str}")
def get_strategy_account(username:str, db: Session = Depends(get_db)):
    integration = BrokerIntegration()
    return integration.get_startegy_account(username, db)