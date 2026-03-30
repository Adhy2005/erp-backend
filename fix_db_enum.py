import sys
import os
sys.path.append(os.getcwd())
try:
    from app.db.database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    
    try:
        db.execute(text("ALTER TYPE userrole ADD VALUE 'manager'"))
        db.commit()
        print("Added manager")
    except Exception as e:
        print("Skip manager:", e)
        db.rollback()

    try:
        db.execute(text("ALTER TYPE userrole ADD VALUE 'admin'"))
        db.commit()
        print("Added admin")
    except Exception as e:
        print("Skip admin:", e)
        db.rollback()
    
    db.close()
except Exception as e:
    print("Error:", e)
