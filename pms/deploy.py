#!/usr/bin/env python3
import os
import sys
import subprocess

def run_command(command):
    """Run a shell command and return output"""
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(f"Error: {e}")
        sys.exit(1)

def setup_project():
    """Setup the project for deployment"""
    print("Setting up PMS Project...")
    
    # Create necessary directories
    directories = ['instance', 'uploads', 'static/css', 'static/js', 'templates/admin', 'templates/faculty', 'templates/student']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")
    
    # Install requirements
    print("Installing requirements...")
    run_command("pip install -r requirements.txt")
    
    # Initialize database
    print("Initializing database...")
    from app import app, db
    with app.app_context():
        db.create_all()
        print("Database created successfully!")
    
    print("\n✅ Setup completed successfully!")
    print("\n🎯 Next steps:")
    print("1. Run: python app.py")
    print("2. Open: http://localhost:5000")
    print("3. Admin login: admin@pms.com / admin123")

if __name__ == "__main__":
    setup_project()