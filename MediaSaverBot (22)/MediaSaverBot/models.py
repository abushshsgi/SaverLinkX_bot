import os
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped
from sqlalchemy import Integer, String, DateTime, Boolean, ForeignKey, Float
from typing import Optional, List
from flask_sqlalchemy import SQLAlchemy

# Base model class
class Base(DeclarativeBase):
    pass


# Create a single SQLAlchemy instance for the whole application
db = SQLAlchemy(model_class=Base)

def init_db(app):
    """Initialize database with the Flask app - use this to avoid duplicate initializations"""
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
    
    db.init_app(app)
    
    # Only create tables if they don't exist
    with app.app_context():
        try:
            # Create tables
            db.create_all()
        except Exception as e:
            # Tables likely already exist, just log the error
            print(f"Note: {str(e)}")
            pass


class User(db.Model):
    """User model to track bot users."""
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<User {self.user_id}: {self.username or self.first_name}>"


class Download(db.Model):
    """Download model to track user downloads."""
    __tablename__ = 'downloads'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.user_id'))
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'youtube', 'instagram', etc.
    file_size: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Size in MB
    status: Mapped[str] = mapped_column(String(20), default='success')  # 'success', 'failed', etc.
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Download {self.id}: {self.source_type} - {self.status}>"


class Donation(db.Model):
    """Donation model to track when users click on donation links."""
    __tablename__ = 'donations'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.user_id'))
    clicked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    context: Mapped[str] = mapped_column(String(50), nullable=True)  # e.g., 'after_download', 'donate_command'
    
    def __repr__(self):
        return f"<Donation {self.id}: User {self.user_id}>"