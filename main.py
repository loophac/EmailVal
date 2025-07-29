from fastapi import FastAPI, Query, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, ValidationError, parse_obj_as
import dns.resolver
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import os
import time
import asyncio
import redis.asyncio as redis

from database import init_db, get_session
from models import APIKey, Log
from admin import router as admin_router
from sqlmodel import select

app = FastAPI()
app.add_middleware(SessionMiddleware,
                   secret_key=os.getenv("SECRET_KEY", "your_fallback_dev_key"))
app.include_router(admin_router)

init_db()

# --- Redis Setup ---
redis_client = redis.from_url("redis://localhost", decode_responses=True)

TIER_LIMITS_PER_MIN = {"free": 60, "basic": 120, "pro": 300, "unlimited": 1200}

TIER_LIMITS_PER_MONTH = {
    "free": 500,
    "basic": 5000,
    "pro": 25000,
    "unlimited": -1
}


def get_monthly_limit(tier: str) -> int:
    return TIER_LIMITS_PER_MONTH.get(tier, 500)


# --- Disposable domains & role list ---
DISPOSABLE_DOMAINS = set()
with open("domains/disposable.txt", "r") as f:
    for line in f:
        DISPOSABLE_DOMAINS.add(line.strip().lower())

ROLE_ADDRESSES = {"admin", "info", "support", "contact", "sales"}


# --- Models ---
class ValidationResult(BaseModel):
    email: str
    is_valid: bool
    syntax_valid: bool
    mx_valid: bool
    is_disposable: bool
    is_role_address: bool
    score: float
    message: str


# --- Utility Functions ---
def validate_syntax(email: str) -> bool:
    try:
        parse_obj_as(EmailStr, email)
        return True
    except ValidationError as e:
        print(f"Syntax check failed: {e}")
        return False


def get_domain(email: str) -> str:
    return email.split("@")[1].lower()


def check_mx(domain: str) -> bool:
    try:
        records = dns.resolver.resolve(domain, 'MX')
        return len(records) > 0
    except Exception as e:
        print(f"MX lookup failed for {domain}: {e}")
        return False


def is_disposable(email: str) -> bool:
    return get_domain(email) in DISPOSABLE_DOMAINS


def is_role(email: str) -> bool:
    return email.split("@")[0].lower() in ROLE_ADDRESSES


def get_daily_limit(tier: str) -> int:
    return {"free": 100, "pro": 5000, "unlimited": -1}.get(tier, 100)


async def is_rate_limited(api_key: str, tier: str) -> bool:
    now = int(time.time()) // 60
    key = f"rate:{api_key}:{now}"
    limit = TIER_LIMITS_PER_MIN.get(tier, 60)

    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, 60)
    return count > limit


# --- Email Validation Endpoint ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
	print("Unhandled Exception:", traceback.format_exc())
	return JSONResponse(
		status_code=500,
		content={"detail": "Internal Server Error"}
	)

@app.get("/validate")
async def validate(email: str = Query(
    ..., examples={"example": {
        "value": "test@example.com"
    }}),
                   x_api_key: str = Header(None)):

    with get_session() as session:
        key_obj = session.exec(
            select(APIKey).where(APIKey.key == x_api_key,
                                 APIKey.active == True)).first()

        if not key_obj:
            return JSONResponse(status_code=403,
                                content={
                                    "success": False,
                                    "data": None,
                                    "error": "Invalid or missing API key"
                                })

    if not key_obj:
        return JSONResponse(status_code=403,
                            content={
                                "success": False,
                                "data": None,
                                "error": "Invalid or missing API key"
                            })

    # Rate limit by minute
    if await is_rate_limited(x_api_key, key_obj.tier):
        return JSONResponse(status_code=429,
                            content={
                                "success": False,
                                "data": None,
                                "error": "Rate limit exceeded for this minute"
                            })

    # Monthly usage check
    monthly_limit = get_monthly_limit(key_obj.tier)
    if monthly_limit != -1:
        now = datetime.utcnow()
        start_of_month = datetime(now.year, now.month, 1)

        usage_this_month = session.exec(
            select(Log).where(Log.api_key_id == key_obj.id, Log.timestamp
                              >= start_of_month)).all()

        if len(usage_this_month) >= monthly_limit:
            return JSONResponse(status_code=429,
                                content={
                                    "success": False,
                                    "data": None,
                                    "error": "Monthly usage limit reached"
                                })

    # Syntax check
    syntax = validate_syntax(email)
    if not syntax:
        return {
            "success": False,
            "data": None,
            "error": "Invalid email syntax"
        }

    domain = get_domain(email)
    mx = check_mx(domain)
    disposable = is_disposable(email)
    role = is_role(email)

    score = 0.0
    if syntax: score += 0.4
    if mx: score += 0.3
    if not disposable: score += 0.2
    if not role: score += 0.1

    # Log request
    session.add(
        Log(email_validated=email,
            timestamp=datetime.utcnow(),
            api_key_id=key_obj.id))
    session.commit()

    result = {
        "email": email,
        "is_valid": score >= 0.5,
        "syntax_valid": syntax,
        "mx_valid": mx,
        "is_disposable": disposable,
        "is_role_address": role,
        "score": round(score, 2),
        "message": "Validation complete"
    }

    return {"success": True, "data": result, "error": None}


# --- Health Check Endpoint ---
@app.get("/health")
def health():
    return {"status": "ok"}
