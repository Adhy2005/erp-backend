import sys
import os
sys.path.append(os.getcwd())
try:
    from app.db.database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    
    try:
        db.execute(text("ALTER TYPE userrole ADD VALUE 'founder'"))
        db.commit()
        print("Added founder")
    except Exception as e:
        print("Skip founder:", e)
        db.rollback()

    try:
        db.execute(text("ALTER TYPE userrole ADD VALUE 'co_founder'"))
        db.commit()
        print("Added co_founder")
    except Exception as e:
        print("Skip co_founder:", e)
        db.rollback()
    
    db.close()
except Exception as e:
    print("Error:", e)
