import os
import re
from werkzeug.utils import secure_filename

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_roll_no(roll_no):
    """
    Validates roll number format. 
    Accepts alphanumeric string between 5 and 20 characters.
    Must contain at least one letter and one number.
    """
    pattern = r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9]{5,20}$'
    return re.match(pattern, roll_no) is not None
