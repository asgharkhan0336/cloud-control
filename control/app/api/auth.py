from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import timedelta

from app.database import get_db
from app.auth.auth import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_current_superuser,
    create_api_key,
    hash_password,
)
from app.models.database import User, APIKey, ResourceQuota

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class APIKeyCreate(BaseModel):
    key_name: str
    expires_days: Optional[int] = None

class APIKeyResponse(BaseModel):
    id: int
    key_name: str
    is_active: bool
    last_used: Optional[str]
    created_at: str
    expires_at: Optional[str]
    
    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    try:
        # Create user
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
            full_name=user_data.full_name
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Create default quota
        quota = ResourceQuota(user_id=user.id)
        db.add(quota)
        db.commit()
        
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )

@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login with username and password"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(hours=24)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@router.post("/api-keys", response_model=dict)
async def create_new_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new API key"""
    api_key = create_api_key(db, current_user.id, key_data.key_name, key_data.expires_days)
    
    return {
        "api_key": api_key,
        "key_name": key_data.key_name,
        "message": "Store this API key securely. It won't be shown again."
    }

@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all API keys for current user"""
    api_keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    return api_keys

@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Revoke an API key"""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    api_key.is_active = False
    db.commit()
    
    return {"message": "API key revoked"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user

# Admin endpoints
@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db)
):
    """List all users (admin only)"""
    users = db.query(User).all()
    return users
