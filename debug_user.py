import uuid
from dotenv import load_dotenv
load_dotenv()

from app.db.database import SessionLocal
from app.models.users import User

db = SessionLocal()
user = db.query(User).filter(User.email == "admin@erp.com").first()

if user:
    print(f"User Found: {user.email}")
    print(f"Role: {user.role} (type: {type(user.role)})")
    print(f"Is Active: {user.is_active}")
    print(f"ID: {user.id}")
else:
    print("User 'admin@erp.com' not found in database.")

db.close()
