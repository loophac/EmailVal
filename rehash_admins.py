from sqlmodel import SQLModel, Session, create_engine, select
from models import AdminUser
import bcrypt

DATABASE_URL = "sqlite:///./database.db"
engine = create_engine(DATABASE_URL)

SQLModel.metadata.create_all(engine)

with Session(engine) as session:
    admins = session.exec(select(AdminUser)).all()
    for admin in admins:
        if not admin.password_hash.startswith("$2b$"):
            hashed = bcrypt.hashpw(admin.password_hash.encode(), bcrypt.gensalt()).decode()
            admin.password_hash = hashed
            session.add(admin)
    session.commit()

print("Rehash complete.")
