from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://cloud_admin:CloudPlatform2024!@localhost/cloud_platform"
)

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Import models to register them with Base
from app.models.database import User, APIKey, VM, ResourceQuota, BillingRecord
