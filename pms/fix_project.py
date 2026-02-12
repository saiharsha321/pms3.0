# fix_project.py
import os

def create_file(filepath, content):
    """Create a file with the given content"""
    try:
        # Create directory if it doesn't exist
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ Created: {filepath}")
    except Exception as e:
        print(f"❌ Error creating {filepath}: {e}")

def main():
    print("🔧 Fixing PMS Project...")
    
    # Fix utils.py with correct roll number validation
    utils_content = '''import os
import re
from werkzeug.utils import secure_filename

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    return '.' in filename and \\
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_roll_no(roll_no):
    """
    Validates roll number format for JNTUK: 24N81A6261
    Pattern: 2 digits (year) + 1 letter + 2 digits + 1 letter + 4 digits
    Examples: 24N81A6261, 23N81B1234, 22N82C5678
    """
    pattern = r'^\\d{2}[A-Z]\\d{2}[A-Z]\\d{4}$'
    return re.match(pattern, roll_no) is not None
'''
    create_file('utils.py', utils_content)
    
    print("✅ Project fixes completed!")
    print("🎯 Restart your application: python app.py")

if __name__ == "__main__":
    main()