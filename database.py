"""
Database models and configuration for Fake News Detector
Uses SQLAlchemy ORM with SQLite
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Database configuration - supports Docker environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./predictions.db")

# Create engine
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=False  # Set to True for SQL query logging
)

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


class Prediction(Base):
    """
    Model for storing news predictions and user feedback
    """
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    prediction = Column(String(10), nullable=False)  # 'REAL' or 'FAKE'
    confidence = Column(Float, nullable=False)
    latency_seconds = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # User feedback fields
    user_feedback = Column(String(20), nullable=True)  # 'correct', 'incorrect', or NULL
    user_rating = Column(Integer, nullable=True)  # 1-5 or NULL
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Prediction(id={self.id}, prediction={self.prediction}, confidence={self.confidence})>"

    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "latency_seconds": self.latency_seconds,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_feedback": self.user_feedback,
            "user_rating": self.user_rating,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


def init_db():
    """
    Initialize the database by creating all tables
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully!")


def get_db():
    """
    Dependency function to get database session
    Yields a database session and ensures it's closed after use
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize database on module import
if __name__ != "__main__":
    # Create tables if they don't exist
    if not os.path.exists("predictions.db"):
        init_db()
    else:
        # Ensure tables exist even if db file exists
        Base.metadata.create_all(bind=engine)
