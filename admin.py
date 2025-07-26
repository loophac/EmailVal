from fastapi import APIRouter, Request, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlmodel import select, func
from database import get_session
from models import AdminUser, APIKey, Log
import bcrypt
import secrets
from datetime import datetime

router = APIRouter()
templates = Jinja2Templates(directory="templates")

ADMIN_USERNAME = "admin"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def get_current_user(request: Request):
    return request.session.get("user")


@router.get("/admin/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/admin/login")
def login(request: Request,
          username: str = Form(...),
          password: str = Form(...),
          session=Depends(get_session)):
    result = session.exec(
        select(AdminUser).where(AdminUser.username == username)).first()
    if result and verify_password(password, result.password_hash):
        request.session["user"] = username
        return RedirectResponse(url="/admin/dashboard",
                                status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Invalid credentials"
    })


@router.get("/admin/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, session=Depends(get_session)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/admin/login")

    keys = session.exec(select(APIKey)).all()
    logs = session.exec(select(Log).order_by(
        Log.timestamp.desc()).limit(50)).all()

    total_logs = session.exec(select(func.count()).select_from(Log)).one()

    now = datetime.utcnow()
    start_of_month = datetime(now.year, now.month, 1)
    monthly_logs = session.exec(
        select(func.count()).select_from(Log).where(
            Log.timestamp >= start_of_month)).one()

    key_data = []
    for key in keys:
        total_calls = session.exec(
            select(func.count()).select_from(Log).where(
                Log.api_key_id == key.id)).one()

        monthly_calls = session.exec(
            select(func.count()).select_from(Log).where(
                Log.api_key_id == key.id, Log.timestamp
                >= start_of_month)).one()

        key_data.append({
            "id": key.id,
            "key": key.key,
            "label": key.label,
            "tier": key.tier,
            "active": key.active,
            "created_at": key.created_at,
            "total_calls": total_calls,
            "monthly_calls": monthly_calls
        })

    return templates.TemplateResponse(
        "dashboard.html", {
            "request": request,
            "user": user,
            "keys": key_data,
            "logs": logs,
            "total_logs": total_logs,
            "monthly_logs": monthly_logs
        })


@router.post("/admin/add-key")
def add_key(request: Request,
            label: str = Form(None),
            tier: str = Form("free"),
            session=Depends(get_session)):
    user = get_current_user(request)
    if not user or user != ADMIN_USERNAME:
        print("Unauthorized attempt to add key.")
        return RedirectResponse("/admin/login",
                                status_code=status.HTTP_302_FOUND)

    if tier not in {"free", "basic", "pro", "unlimited"}:
        print(f"Invalid tier specified: {tier}")
        return RedirectResponse("/admin/dashboard",
                                status_code=status.HTTP_302_FOUND)

    try:
        new_key = APIKey(label=label or "Untitled Key", tier=tier)
        session.add(new_key)
        session.commit()
        print(f"New API key created: {new_key.key}")
    except Exception as e:
        print(f"Error creating API key: {e}")

    return RedirectResponse("/admin/dashboard",
                            status_code=status.HTTP_302_FOUND)


@router.post("/admin/toggle-key")
def toggle_key(request: Request,
               key_id: int = Form(...),
               session=Depends(get_session)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/admin/login")
    key = session.get(APIKey, key_id)
    if key:
        key.active = not key.active
        session.add(key)
        session.commit()
    return RedirectResponse("/admin/dashboard",
                            status_code=status.HTTP_302_FOUND)


@router.get("/admin/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login")
