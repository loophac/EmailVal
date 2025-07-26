from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import secrets


class APIKey(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(default_factory=lambda: secrets.token_hex(16),
                     index=True,
                     unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = Field(default=True)
    label: Optional[str] = None
    tier: str = Field(default="free")  # 'free', 'basic', 'pro', 'unlimited'


class AdminUser(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str


class Log(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email_validated: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    api_key_id: Optional[int] = Field(default=None, foreign_key="apikey.id")
    ip_address: Optional[str] = None
