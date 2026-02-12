import sqlite3
import os

def update_database():
    # Use absolute path relative to this script
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_path = os.path.join(basedir, 'instance', 'pms.db')
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Add columns to user table
        print("Checking User table columns...")
        cursor.execute("PRAGMA table_info(user)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'is_verified' not in columns:
            print("Adding is_verified column...")
            cursor.execute("ALTER TABLE user ADD COLUMN is_verified BOOLEAN DEFAULT 0")
            
        if 'otp' not in columns:
            print("Adding otp column...")
            cursor.execute("ALTER TABLE user ADD COLUMN otp VARCHAR(6)")
            
        if 'otp_expiry' not in columns:
            print("Adding otp_expiry column...")
            cursor.execute("ALTER TABLE user ADD COLUMN otp_expiry DATETIME")
            
        if 'is_blocked' not in columns:
            print("Adding is_blocked column...")
            cursor.execute("ALTER TABLE user ADD COLUMN is_blocked BOOLEAN DEFAULT 0")

        if 'incharge_department' not in columns:
            print("Adding incharge_department column...")
            cursor.execute("ALTER TABLE user ADD COLUMN incharge_department VARCHAR(50)")
            
        if 'incharge_section' not in columns:
            print("Adding incharge_section column...")
            cursor.execute("ALTER TABLE user ADD COLUMN incharge_section VARCHAR(10)")

        # Create department table if not exists
        print("Checking Department table...")
        # Create system_config table if not exists
        print("Checking SystemConfig table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_config (
                id INTEGER PRIMARY KEY,
                key VARCHAR(50) UNIQUE NOT NULL,
                value VARCHAR(255),
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Seed default SMTP settings if not exists
        default_configs = {
            'MAIL_SERVER': 'smtp.gmail.com',
            'MAIL_PORT': '587',
            'MAIL_USERNAME': 'pms.garuda16@gmail.com',
            'MAIL_PASSWORD': 'Harsha@16', # User provided
            'MAIL_USE_TLS': 'True'
        }
        
        for key, value in default_configs.items():
            cursor.execute("SELECT id FROM system_config WHERE key = ?", (key,))
            if not cursor.fetchone():
                print(f"Seeding default config: {key}")
                cursor.execute("INSERT INTO system_config (key, value) VALUES (?, ?)", (key, value))

        conn.commit()
        print("Database updated successfully!")

    except Exception as e:
        print(f"Error updating database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_database()
