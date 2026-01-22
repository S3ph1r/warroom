"""
WAR ROOM - Database Configuration
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://warroom:warroom_dev_password@localhost:5432/warroom_db")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables"""
    from db.models import (
        Holding, Transaction, ImportLog,
        CouncilSession, PortfolioSnapshot, PriceAlert
    )
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")
