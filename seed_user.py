"""
seed_user.py
------------
Run this once to create a test admin user in the DB and print a JWT token.
Usage: python seed_user.py
"""

import uuid
from dotenv import load_dotenv
load_dotenv()

from app.db.database import SessionLocal, engine, Base
from app.models.users import User
from app.db.enums import UserRole
from app.middleware.auth import create_access_token
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()

# Check if test user already exists
existing = db.query(User).filter(User.email == "admin@erp.com").first()
if existing:
    print("✅ User already exists: admin@erp.com")
    user = existing
else:
    user = User(
        id=uuid.uuid4(),
        email="admin@erp.com",
        password_hash=pwd_context.hash("admin123"),
        full_name="Admin User",
        role=UserRole.super_admin,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print("✅ Created user: admin@erp.com / admin123")

# Generate JWT token
token = create_access_token({
    "sub": user.email,
    "role": str(user.role.value),
    "user_id": str(user.id),
})

print("\n🔑 JWT Token for Swagger:")
print("-" * 60)
print(token)
print("-" * 60)
print("\n📋 How to use in Swagger (http://127.0.0.1:8000/docs):")
print("  1. Click the green 'Authorize 🔓' button (top right)")
print("  2. Paste the token above into the 'Value' field")
print("  3. Click 'Authorize' → 'Close'")
print("  4. Now all endpoints work!")

db.close()
