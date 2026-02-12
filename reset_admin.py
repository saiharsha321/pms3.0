import sys
import os

# Change sys path so we can import modules from pms folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'pms')))

from app import app, db
from models import User

def reset_admin():
    with app.app_context():
        # Find admin
        admin = User.query.filter_by(role='admin').first()
        
        if admin:
            print(f"Admin found: {admin.email}")
            admin.set_password('admin123')
            db.session.commit()
            print("Password reset to: admin123")
        else:
            print("Admin not found. Creating new admin...")
            admin = User(
                email='admin@pms.com',
                first_name='System',
                last_name='Admin',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin created.")
            print("Email: admin@pms.com")
            print("Password: admin123")

if __name__ == "__main__":
    reset_admin()
