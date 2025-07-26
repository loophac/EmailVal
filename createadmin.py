from sqlmodel import Session, select
from database import engine
from models import AdminUser
import bcrypt

# ----- CONFIG -----
username = "admin"
password = "changeme123"  # Change this immediately after login!

hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

with Session(engine) as session:
    existing = session.exec(select(AdminUser).where(AdminUser.username == username)).first()
    if existing:
        print(f"Admin user '{username}' already exists.")
    else:
        user = AdminUser(username=username, password_hash=hashed_pw)
        session.add(user)
        session.commit()
        print(f"✅ Admin user '{username}' created successfully!")
