import sys
import os
import shutil

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'pms')))

from app import app, db
from models import User, Permission
from config import Config

def cleanup():
    with app.app_context():
        print("Starting cleanup...")

        # 1. Clear Uploads
        upload_folder = app.config['UPLOAD_FOLDER']
        if os.path.exists(upload_folder):
            print(f"Cleaning uploads folder: {upload_folder}")
            for filename in os.listdir(upload_folder):
                file_path = os.path.join(upload_folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")
            print("Uploads cleared.")
        else:
            print("Uploads folder not found.")

        # 2. Delete Permissions
        num_permissions = Permission.query.delete()
        print(f"Deleted {num_permissions} permission records.")

        # 3. Delete Users (Keep Admin, Faculty, HOD, and specific email)
        # We want to keep:
        # - role == 'admin'
        # - role == 'faculty'
        # - role == 'hod' (Assuming HODs should be kept as they are senior faculty)
        # - email == 'anjaiahanjanna9@gmail.com'
        
        users_to_delete = User.query.filter(
            User.role.notin_(['admin', 'faculty', 'hod']),
            User.email != 'anjaiahanjanna9@gmail.com'
        ).all()
        
        count = 0
        for user in users_to_delete:
            db.session.delete(user)
            count += 1
            
        print(f"Deleted {count} student accounts.")
        
        db.session.commit()
        print("Database cleanup complete.")
        print("Remaining Users:")
        for u in User.query.all():
            print(f"- {u.first_name} ({u.role}) - {u.email}")

if __name__ == "__main__":
    cleanup()
