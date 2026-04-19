from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import secrets
import hashlib

from app.database import get_db
from app.models.database import User, APIKey

# Generate a secret key
SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# Simple password hashing using SHA-256 with salt
def hash_password(password: str) -> str:
    """Hash a password using SHA-256 with salt"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${password_hash}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        salt, stored_hash = hashed_password.split('$')
        calculated_hash = hashlib.sha256((plain_password + salt).encode()).hexdigest()
        return calculated_hash == stored_hash
    except:
        return False

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate a user by username and password"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current superuser"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

def create_api_key(db: Session, user_id: int, key_name: str, expires_days: Optional[int] = None) -> str:
    """Create a new API key for a user"""
    api_key = f"cp_{secrets.token_urlsafe(32)}"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    expires_at = None
    if expires_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_days)
    
    api_key_record = APIKey(
        user_id=user_id,
        key_name=key_name,
        api_key_hash=api_key_hash,
        expires_at=expires_at
    )
    
    db.add(api_key_record)
    db.commit()
    
    return api_key
