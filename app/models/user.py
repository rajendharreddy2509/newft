from datetime import datetime, timezone, time
from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, DateTime, Text, Time
from sqlalchemy.orm import relationship
from app.database.connection import Base, engine

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    mobile = Column(String(20), unique=True, nullable=False)
    
    max_loss = Column(String(500), default="0")
    max_profit = Column(String(500), default="0")
    subscription_start_date = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    subscription_end_date = Column(DateTime(timezone=True))
    is_on_trial = Column(Boolean, default=True)
    num_of_users = Column(Integer, default=1)  
    subscription_type = Column(String(50), default='Free_Trial')  
    payment_order_id = Column(String(100), nullable=True)  
    payment_amount = Column(String(100), default="0") 
    payment_mode = Column(String(100), nullable=True) 
    renewal_period = Column(String(100))
    is_admin = Column(Boolean, default=False)
    
    broker_credentials = relationship("BrokerCredentials", back_populates="user", lazy=True)
    strategies = relationship('Strategies', back_populates="user", lazy=True)  # Establish relationship with Strategies

class Broker(Base):
    __tablename__ = 'brokers'
    
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(String(100), unique=True, nullable=False)
    renewal_period = Column(String(100))

class BrokerCredentials(Base):
    __tablename__ = "broker_credentials"

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    username = Column(String(50))
    broker = Column(String(500))
    broker_user_id = Column(String(500))
    password = Column(Text)  # encrypted password
    api_key = Column(Text)   # encrypted API key
    qr_code = Column(Text)   # encrypted QR code
    secret_key = Column(Text, nullable=True)  # encrypted secret key
    client_id = Column(String(50))
    imei = Column(Text, nullable=True)  # encrypted IMEI
    vendor_code = Column(String(150))
    margin = Column(Text)
    enabled = Column(Boolean, default=True)
    display_name = Column(String(500))
    redirect_url = Column(String(500))
    max_loss = Column(String(500), default="0")
    max_profit = Column(String(500), default="0")
    profit_locking = Column(String(500), default=',,,')
    reached_profit = Column(Float, default=0)  
    locked_min_profit = Column(Float, default=0)
    available_balance = Column(String(500), default="0.00")
    user_multiplier = Column(String(500), default="1")
    max_loss_per_trade = Column(String(500), default="0")
    utilized_margin = Column(String(500), default="0")
    max_open_trades = Column(String(500), default="1")
    exit_time = Column(Time, default=time(0, 0, 0))

    user = relationship("User", back_populates="broker_credentials")

class Strategies(Base):
    __tablename__ = 'strategies'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    alias = Column(String(50))
    strategy_tag = Column(String(50), unique=True, nullable=False)
    broker = Column(String(500))
    broker_user_id = Column(String(500))
    max_loss = Column(String(500), default="0")
    max_profit = Column(String(500), default="0")
    profit_locking = Column(String(500), default=',,,')
    reached_profit = Column(Float, default=0)
    locked_min_profit = Column(Float, default=0)
    open_time = Column(Time, default=time(0, 0, 0))
    close_time = Column(Time, default=time(0, 0, 0))
    square_off_time = Column(Time, default=time(0, 0, 0))
    allowed_trades = Column(String(100), default="Both")
    entry_order_retry = Column(Boolean, default=False)
    entry_retry_count = Column(String(100), default="0")
    entry_retry_wait = Column(String(500), default="0")
    exit_order_retry = Column(Boolean, default=False)
    exit_retry_count = Column(String(100), default="0")
    exit_retry_wait = Column(String(500), default="0")
    exit_max_wait = Column(String(500), default="0")

    # Relationship to StrategyMultipliers
    multipliers = relationship('StrategyMultipliers', back_populates='strategy', lazy=True, cascade="all, delete-orphan")

    # Missing relationship to User
    user = relationship("User", back_populates="strategies")

class StrategyMultipliers(Base):
    __tablename__ = 'strategy_multipliers'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=False)
    broker_user_id = Column(String(50), nullable=False)
    multiplier = Column(String(50))

    # Define the relationship back to Strategies
    strategy = relationship('Strategies', back_populates='multipliers')

# Create all tables in the database
Base.metadata.create_all(bind=engine)
