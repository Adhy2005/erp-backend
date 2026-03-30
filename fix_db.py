from app.db.database import engine
from sqlalchemy import text

statements = [
    "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS sprint_id UUID;",
    "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS parent_task_id UUID;",
    "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS order_index INTEGER;",
]

with engine.connect() as conn:
    for stmt in statements:
        try:
            conn.execute(text(stmt))
        except Exception as e:
            print("Error:", e)
    
    try:
        conn.execute(text("CREATE TYPE taskpriority AS ENUM ('low', 'medium', 'high');"))
    except Exception as e:
        print("Enum error:", e)

    try:
        conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS priority taskpriority;"))
    except Exception as e:
        print("Error:", e)
        
    conn.commit()
    print("DB schema updated!")
