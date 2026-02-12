import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, send_from_directory, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from models import db, User, Club, Event, Permission, Department, SystemConfig
from config import Config
from utils import allowed_file, validate_roll_no
import random
import string

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
mail = Mail(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create uploads directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('instance', exist_ok=True)

# Create tables and admin user
with app.app_context():
    db.create_all()
    # Create admin user if not exists
    if not User.query.filter_by(role='admin').first():
        admin = User(
            email='admin@pms.com',
            first_name='System',
            last_name='Admin',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Create sample HOD user
        hod = User(
            email='hod@college.edu',
            first_name='HOD',
            last_name='CSE',
            role='hod',
            department='CSE'
        )
        hod.set_password('hod123')
        db.session.add(hod)
        
        # Create sample clubs and events
        club1 = Club(name='Technical Club', description='Technical events and workshops')
        club2 = Club(name='Cultural Club', description='Cultural activities and events')
        club3 = Club(name='Sports Club', description='Sports and games')
        
        db.session.add_all([club1, club2, club3])
        db.session.commit()
        
        # Create sample events
        event1 = Event(club_id=club1.id, name='Code Hackathon', description='Annual coding competition', date=datetime(2024, 2, 15), venue='CS Lab')
        event2 = Event(club_id=club2.id, name='Cultural Fest', description='Annual cultural festival', date=datetime(2024, 3, 1), venue='Auditorium')
        event3 = Event(club_id=club3.id, name='Sports Tournament', description='Inter-college sports tournament', date=datetime(2024, 2, 20), venue='Sports Ground')
        
        db.session.add_all([event1, event2, event3])
        db.session.commit()

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin_dashboard'))
        elif current_user.is_student():
            return redirect(url_for('student_dashboard'))
        else:
            return redirect(url_for('faculty_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if user.is_blocked:
                flash('Your account has been blocked. Please contact admin.', 'danger')
                return redirect(url_for('login'))
                
            if user.role == 'student' and not user.is_verified:
                flash('Please verify your email first', 'warning')
                return redirect(url_for('verify_otp', user_id=user.id))
                
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/student-signup', methods=['GET', 'POST'])
def student_signup():
    if request.method == 'POST':
        roll_no = request.form.get('roll_no').upper() # Force Uppercase
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        section = request.form.get('section')
        department = request.form.get('department')
        
        if not validate_roll_no(roll_no):
            flash('Invalid roll number. Must be 5-20 chars, alphanumeric, with at least 1 letter and 1 number (e.g., 24N81A6261).', 'danger')
            # Re-render properly involves passing back data, but for now just validation msg
            departments = Department.query.all() # Need to re-fetch departments
            return render_template('student_signup.html', departments=departments)
        
        if User.query.filter_by(roll_no=roll_no).first():
            flash('Roll number already registered', 'danger')
            return render_template('student_signup.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return render_template('student_signup.html')
        
        student = User(
            roll_no=roll_no,
            email=email,
            first_name=first_name,
            last_name=last_name,
            section=section,
            department=department,
            role='student',
            is_verified=False
        )
        student.set_password(password)
        
        # Generate OTP
        otp = ''.join(random.choices(string.digits, k=6))
        student.otp = otp
        student.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        
        db.session.add(student)
        db.session.commit()
        
        # Send OTP
        print(f"DEBUG: Generated OTP for {email}: {otp}") # Print to console for local testing
        try:
            # Fetch dynamic SMTP settings
            smtp_config = {}
            configs = SystemConfig.query.all()
            for config in configs:
                smtp_config[config.key] = config.value
            
            # Check if SMTP is configured (basic check)
            if smtp_config.get('MAIL_USERNAME') and smtp_config.get('MAIL_PASSWORD'):
                # Create a new mail connection with dynamic settings
                app.config.update(
                    MAIL_SERVER=smtp_config.get('MAIL_SERVER', 'smtp.gmail.com'),
                    MAIL_PORT=int(smtp_config.get('MAIL_PORT', 587)),
                    MAIL_USERNAME=smtp_config.get('MAIL_USERNAME'),
                    MAIL_PASSWORD=smtp_config.get('MAIL_PASSWORD'),
                    MAIL_USE_TLS=smtp_config.get('MAIL_USE_TLS') == 'True'
                )
                mail = Mail(app) # Re-init mail with new config
                
                msg = Message('Verify your PMS Account',
                            sender=app.config['MAIL_USERNAME'],
                            recipients=[email])
                msg.body = f'Your OTP is: {otp}. It expires in 10 minutes.'
                mail.send(msg)
                flash('Registration successful! Please check your email for OTP.', 'info')
            else:
                flash('Registration successful! OTP printed to console (Dev Mode/SMTP Not Configured).', 'info')
            
            return redirect(url_for('verify_otp', user_id=student.id))
        except Exception as e:
            print(f"Error sending email: {e}")
            flash('Error sending email. Check console for OTP.', 'warning')
            return redirect(url_for('verify_otp', user_id=student.id))
    
    # Fetch departments for the dropdown
    departments = Department.query.all()
    return render_template('student_signup.html', departments=departments)

@app.route('/verify-otp/<int:user_id>', methods=['GET', 'POST'])
def verify_otp(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_verified:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        otp = request.form.get('otp')
        if user.otp == otp and user.otp_expiry > datetime.utcnow():
            user.is_verified = True
            user.otp = None
            user.otp_expiry = None
            db.session.commit()
            flash('Account verified successfully! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid or expired OTP', 'danger')
            
    return render_template('verify_otp.html', email=user.email)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            otp = ''.join(random.choices(string.digits, k=6))
            user.otp = otp
            user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
            db.session.commit()
            
            print(f"DEBUG: Password Reset OTP for {email}: {otp}") # Print to console
            try:
                # Fetch dynamic SMTP settings
                smtp_config = {}
                configs = SystemConfig.query.all()
                for config in configs:
                    smtp_config[config.key] = config.value
                
                if smtp_config.get('MAIL_USERNAME') and smtp_config.get('MAIL_PASSWORD'):
                     # Create a new mail connection with dynamic settings
                    app.config.update(
                        MAIL_SERVER=smtp_config.get('MAIL_SERVER', 'smtp.gmail.com'),
                        MAIL_PORT=int(smtp_config.get('MAIL_PORT', 587)),
                        MAIL_USERNAME=smtp_config.get('MAIL_USERNAME'),
                        MAIL_PASSWORD=smtp_config.get('MAIL_PASSWORD'),
                        MAIL_USE_TLS=smtp_config.get('MAIL_USE_TLS') == 'True'
                    )
                    mail = Mail(app) # Re-init mail with new config
                    
                    msg = Message('Reset your PMS Password',
                                sender=app.config['MAIL_USERNAME'],
                                recipients=[email])
                    msg.body = f'Your Password Reset OTP is: {otp}. It expires in 10 minutes.'
                    mail.send(msg)
                else:
                    flash('OTP printed to console (Dev Mode)', 'info')
                
                return redirect(url_for('reset_password', user_id=user.id))
            except Exception as e:
                print(f"Error sending email: {e}")
                flash('Error sending email. Check console for OTP.', 'warning')
                return redirect(url_for('reset_password', user_id=user.id))
        else:
            flash('Email not found', 'danger')
            
    return render_template('forgot_password.html')

@app.route('/reset-password/<int:user_id>', methods=['GET', 'POST'])
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        otp = request.form.get('otp')
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if user.otp == otp and user.otp_expiry > datetime.utcnow():
            if new_password == confirm_password:
                user.set_password(new_password)
                user.otp = None
                user.otp_expiry = None
                db.session.commit()
                flash('Password reset successful', 'success')
                return redirect(url_for('login'))
            else:
                flash('Passwords do not match', 'danger')
        else:
            flash('Invalid or expired OTP', 'danger')
            
    return render_template('reset_password.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# PROFILE ROUTE
@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.email = request.form.get('email')
        current_user.phone = request.form.get('phone')
        
        # Admin can change department, others cannot
        if current_user.is_admin():
            current_user.department = request.form.get('department')
        
        # Handle password change
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password:
            if new_password == confirm_password:
                current_user.set_password(new_password)
                flash('Password updated successfully', 'success')
            else:
                flash('Passwords do not match', 'danger')
                return render_template('edit_profile.html')
        
        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('index'))
    
    return render_template('edit_profile.html')

# Serve uploaded files
@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Admin Routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    stats = {
        'total_students': User.query.filter_by(role='student').count(),
        'total_faculty': User.query.filter(User.role.in_(['faculty', 'hod'])).count(),
        'pending_permissions': Permission.query.filter_by(status='pending').count(),
        'total_clubs': Club.query.count()
    }
    
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/students')
@login_required
def manage_students():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    students = User.query.filter_by(role='student').all()
    return render_template('admin/students.html', students=students)

@app.route('/admin/students/add', methods=['POST'])
@login_required
def add_student():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('manage_students'))

    roll_no = request.form.get('roll_no').upper() # Force Uppercase
    email = request.form.get('email')
    password = request.form.get('password') or 'student123'
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    department = request.form.get('department')
    section = request.form.get('section')
    
    if User.query.filter_by(roll_no=roll_no).first():
        flash('Roll number already exists', 'danger')
        return redirect(url_for('manage_students'))

    if User.query.filter_by(email=email).first():
        flash('Email already exists', 'danger')
        return redirect(url_for('manage_students'))

    student = User(
        roll_no=roll_no,
        email=email,
        first_name=first_name,
        last_name=last_name,
        role='student',
        department=department,
        section=section,
        is_verified=True # Admin created students are auto-verified
    )
    student.set_password(password)
    
    db.session.add(student)
    db.session.commit()
    
    flash('Student added successfully', 'success')
    return redirect(url_for('manage_students'))

@app.route('/admin/students/edit/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('manage_students'))
    
    student = User.query.get_or_404(student_id)
    if student.role != 'student':
        flash('Can only edit student accounts', 'danger')
        return redirect(url_for('manage_students'))
        
    if request.method == 'POST':
        student.first_name = request.form.get('first_name')
        student.last_name = request.form.get('last_name')
        student.email = request.form.get('email')
        student.phone = request.form.get('phone')
        
        # Admin can block/unblock
        is_blocked = request.form.get('is_blocked') == 'on'
        student.is_blocked = is_blocked
        
        # Admin can set password
        password = request.form.get('password')
        if password:
            student.set_password(password)
            
        db.session.commit()
        flash('Student profile updated successfully', 'success')
        return redirect(url_for('manage_students'))
        
    return render_template('admin/edit_student.html', student=student)


@app.route('/admin/students/delete/<int:student_id>')
@login_required
def delete_student(student_id):
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('manage_students'))
    
    student = User.query.get_or_404(student_id)
    if student.role != 'student':
        flash('Can only delete student accounts', 'danger')
        return redirect(url_for('manage_students'))
    
    # Delete associated permissions
    Permission.query.filter_by(student_id=student_id).delete()
    
    db.session.delete(student)
    db.session.commit()
    
    flash('Student deleted successfully', 'success')
    return redirect(url_for('manage_students'))

@app.route('/admin/students/bulk-upload', methods=['POST'])
@login_required
def bulk_upload_students():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('manage_students'))
    
    if 'file' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('manage_students'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('manage_students'))
    
    if file and (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
            created_count = 0
            for _, row in df.iterrows():
                roll_no = str(row['roll_no']).upper()
                if not User.query.filter_by(roll_no=roll_no).first() and validate_roll_no(roll_no):
                    student = User(
                        roll_no=roll_no,
                        email=row['email'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        section=row['section'],
                        department=row.get('department', 'CSE'),
                        role='student'
                    )
                    student.set_password('default123')
                    db.session.add(student)
                    created_count += 1
            
            db.session.commit()
            flash(f'Successfully created {created_count} student accounts', 'success')
        
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'danger')
    else:
        flash('Invalid file type. Please upload CSV or Excel file.', 'danger')
    
    return redirect(url_for('manage_students'))

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Update settings
        configs = {
            'MAIL_SERVER': request.form.get('mail_server'),
            'MAIL_PORT': request.form.get('mail_port'),
            'MAIL_USERNAME': request.form.get('mail_username'),
            'MAIL_PASSWORD': request.form.get('mail_password'),
            'MAIL_USE_TLS': 'True' if request.form.get('mail_use_tls') else 'False'
        }
        
        for key, value in configs.items():
            config = SystemConfig.query.filter_by(key=key).first()
            if config:
                config.value = value
            else:
                new_config = SystemConfig(key=key, value=value)
                db.session.add(new_config)
        
        db.session.commit()
        flash('Settings updated successfully', 'success')
        return redirect(url_for('admin_settings'))
        
    # Fetch current settings
    settings = {}
    configs = SystemConfig.query.all()
    for config in configs:
        settings[config.key] = config.value
        
    return render_template('admin/settings.html', settings=settings)

@app.route('/admin/departments')
@login_required
def manage_departments():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    departments = Department.query.order_by(Department.name).all()
    return render_template('admin/departments.html', departments=departments)

@app.route('/admin/departments/add', methods=['POST'])
@login_required
def add_department():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('manage_departments'))
    
    name = request.form.get('name').upper()
    
    if Department.query.filter_by(name=name).first():
        flash('Department already exists', 'danger')
        return redirect(url_for('manage_departments'))
    
    department = Department(name=name)
    db.session.add(department)
    db.session.commit()
    
    flash('Department added successfully', 'success')
    return redirect(url_for('manage_departments'))

@app.route('/admin/departments/delete/<int:dept_id>')
@login_required
def delete_department(dept_id):
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('manage_departments'))
    
    department = Department.query.get_or_404(dept_id)
    db.session.delete(department)
    db.session.commit()
    
    flash('Department deleted successfully', 'success')
    return redirect(url_for('manage_departments'))

@app.route('/admin/faculty')
@login_required
def manage_faculty():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    faculty = User.query.filter(User.role.in_(['faculty', 'hod'])).all()
    return render_template('admin/faculty.html', faculty=faculty)

@app.route('/admin/faculty/edit/<int:faculty_id>', methods=['GET', 'POST'])
@login_required
def edit_faculty(faculty_id):
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('manage_faculty'))
    
    faculty = User.query.get_or_404(faculty_id)
    if not faculty.is_faculty():
        flash('Can only edit faculty accounts', 'danger')
        return redirect(url_for('manage_faculty'))
        
    if request.method == 'POST':
        faculty.first_name = request.form.get('first_name')
        faculty.last_name = request.form.get('last_name')
        faculty.email = request.form.get('email')
        faculty.phone = request.form.get('phone')
        
        # Block/Unblock
        is_blocked = request.form.get('is_blocked') == 'on'
        faculty.is_blocked = is_blocked
        
        # Password Reset
        password = request.form.get('password')
        if password:
            faculty.set_password(password)
            
        # Class Incharge Assignment
        incharge_dept = request.form.get('incharge_department')
        incharge_sec = request.form.get('incharge_section')
        
        if incharge_dept and incharge_sec:
            faculty.incharge_department = incharge_dept
            faculty.incharge_section = incharge_sec
        else:
            # If cleared
            faculty.incharge_department = None
            faculty.incharge_section = None
            
        db.session.commit()
        flash('Faculty profile updated successfully', 'success')
        return redirect(url_for('manage_faculty'))
        
    # Get departments for dropdown
    departments = Department.query.all()
    return render_template('admin/edit_faculty.html', faculty=faculty, departments=departments)

@app.route('/admin/faculty/delete/<int:faculty_id>')
@login_required
def delete_faculty(faculty_id):
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('manage_faculty'))
    
    faculty = User.query.get_or_404(faculty_id)
    if not faculty.is_faculty():
        flash('Can only delete faculty accounts', 'danger')
        return redirect(url_for('manage_faculty'))
        
    db.session.delete(faculty)
    db.session.commit()
    flash('Faculty deleted successfully', 'success')
    return redirect(url_for('manage_faculty'))

@app.route('/admin/faculty/add', methods=['POST'])
@login_required
def add_faculty():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('manage_faculty'))
    
    email = request.form.get('email')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    role = request.form.get('role')
    department = request.form.get('department')
    
    if User.query.filter_by(email=email).first():
        flash('Email already exists', 'danger')
        return redirect(url_for('manage_faculty'))
    
    faculty = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=role,
        department=department,
    )
    
    password = request.form.get('password')
    if password:
        faculty.set_password(password)
    else:
        faculty.set_password('faculty123')
    
    db.session.add(faculty)
    db.session.commit()
    
    flash('Faculty added successfully', 'success')
    return redirect(url_for('manage_faculty'))



@app.route('/admin/clubs')
@login_required
def manage_clubs():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    clubs = Club.query.all()
    return render_template('admin/clubs.html', clubs=clubs)

@app.route('/admin/clubs/add', methods=['POST'])
@login_required
def add_club():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('manage_clubs'))
    
    name = request.form.get('name')
    description = request.form.get('description')
    
    club = Club(name=name, description=description)
    db.session.add(club)
    db.session.commit()
    
    flash('Club added successfully', 'success')
    return redirect(url_for('manage_clubs'))

@app.route('/admin/clubs/delete/<int:club_id>')
@login_required
def delete_club(club_id):
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('manage_clubs'))
    
    club = Club.query.get_or_404(club_id)
    
    # Check if club has events
    if club.events:
        flash('Cannot delete club that has events. Delete events first.', 'danger')
        return redirect(url_for('manage_clubs'))
    
    db.session.delete(club)
    db.session.commit()
    
    flash('Club deleted successfully', 'success')
    return redirect(url_for('manage_clubs'))

@app.route('/admin/events/add', methods=['POST'])
@login_required
def add_event():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('manage_clubs'))
    
    club_id = request.form.get('club_id')
    name = request.form.get('name')
    description = request.form.get('description')
    date = request.form.get('date')
    venue = request.form.get('venue')
    
    event = Event(
        club_id=club_id,
        name=name,
        description=description,
        date=datetime.strptime(date, '%Y-%m-%d'),
        venue=venue
    )
    db.session.add(event)
    db.session.commit()
    
    flash('Event added successfully', 'success')
    return redirect(url_for('manage_clubs'))

@app.route('/admin/events/delete/<int:event_id>')
@login_required
def delete_event(event_id):
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('manage_clubs'))
    
    event = Event.query.get_or_404(event_id)
    
    # Check if event has permissions
    if event.permissions:
        flash('Cannot delete event that has permission requests.', 'danger')
        return redirect(url_for('manage_clubs'))
    
    db.session.delete(event)
    db.session.commit()
    
    flash('Event deleted successfully', 'success')
    return redirect(url_for('manage_clubs'))

@app.route('/admin/permissions')
@login_required
def admin_permissions():
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    permissions = Permission.query.order_by(Permission.applied_at.desc()).all()
    return render_template('admin/permissions.html', permissions=permissions)

@app.route('/admin/permission/<int:permission_id>')
@login_required
def admin_view_permission(permission_id):
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    permission = Permission.query.get_or_404(permission_id)
    return render_template('admin/permission_details.html', permission=permission)

@app.route('/admin/permission/<int:permission_id>/<action>')
@login_required
def admin_update_permission(permission_id, action):
    if not current_user.is_admin():
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    permission = Permission.query.get_or_404(permission_id)
    
    if action == 'approve':
        permission.status = 'approved'
        permission.approved_by = current_user.id
        permission.approved_at = datetime.utcnow()
        flash('Permission approved', 'success')
    elif action == 'reject':
        permission.status = 'rejected'
        permission.approved_by = current_user.id
        permission.approved_at = datetime.utcnow()
        flash('Permission rejected', 'warning')
    
    db.session.commit()
    return redirect(url_for('admin_permissions'))

# Faculty Routes
@app.route('/faculty/dashboard')
@login_required
def faculty_dashboard():
    if not current_user.is_faculty():
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    # Helper to group permissions
    from itertools import groupby
    
    def group_permissions(permissions):
        # Sort by Date (desc) then Section (asc)
        permissions.sort(key=lambda x: (x.date, x.student.section), reverse=True)
        
        grouped = {}
        # Group by Date
        for date, date_group in groupby(permissions, key=lambda x: x.date):
            date_str = date.strftime('%Y-%m-%d')
            grouped[date_str] = {}
            # Group by Section
            # We need to convert iterator to list to use it multiple times if needed, 
            # but here we just iterate again.
            # However, groupby returns an iterator that consumes the original.
            # We need to collect the date_group first.
            date_perms = list(date_group)
            
            # Now Sort by Section for the inner groupby
            date_perms.sort(key=lambda x: x.student.section)
            
            for section, section_group in groupby(date_perms, key=lambda x: x.student.section):
                grouped[date_str][section] = list(section_group)
        return grouped

    is_incharge = current_user.is_incharge()
    
    if current_user.is_hod():
        # HOD sees pending permissions from their department
        pending_permissions_query = Permission.query.join(
            User, Permission.student_id == User.id
        ).filter(
            User.department == current_user.department,
            Permission.status == 'pending'
        ).all()
        
        pending_grouped = group_permissions(pending_permissions_query)
        
        approved_permissions_query = Permission.query.join(
            User, Permission.student_id == User.id
        ).filter(
            User.department == current_user.department,
            Permission.status == 'approved'
        ).all()
        
        approved_grouped = group_permissions(approved_permissions_query)
        
    elif is_incharge:
        # Class Incharge sees pending permissions from their assigned section
        pending_permissions_query = Permission.query.join(
            User, Permission.student_id == User.id
        ).filter(
            User.department == current_user.incharge_department,
            User.section == current_user.incharge_section,
            Permission.status == 'pending'
        ).all()
        
        pending_grouped = group_permissions(pending_permissions_query)
        
        # Also sees approved permissions from their department (standard faculty view)
        approved_permissions_query = Permission.query.join(
            User, Permission.student_id == User.id
        ).filter(
            User.department == current_user.department,
            Permission.status == 'approved'
        ).all()
        
        approved_grouped = group_permissions(approved_permissions_query)

    else:
        # Regular faculty sees only approved permissions
        pending_grouped = {}
        approved_permissions_query = Permission.query.join(
            User, Permission.student_id == User.id
        ).filter(
            User.department == current_user.department,
            Permission.status == 'approved'
        ).all()
        
        approved_grouped = group_permissions(approved_permissions_query)
    
    return render_template('faculty/dashboard.html', 
                         pending_grouped=pending_grouped,
                         approved_grouped=approved_grouped,
                         is_hod=current_user.is_hod(),
                         is_incharge=is_incharge)

@app.route('/faculty/permission/<int:permission_id>')
@login_required
def view_permission(permission_id):
    if not current_user.is_faculty():
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    permission = Permission.query.get_or_404(permission_id)
    return render_template('faculty/permission_details.html', permission=permission)

@app.route('/faculty/permission/<int:permission_id>/<action>')
@login_required
def update_permission_status(permission_id, action):
    if not current_user.is_faculty():
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    permission = Permission.query.get_or_404(permission_id)
    student = permission.student
    
    # Check authorization
    is_authorized = False
    if current_user.is_hod() and current_user.department == student.department:
        is_authorized = True
    elif current_user.is_incharge() and \
         current_user.incharge_department == student.department and \
         current_user.incharge_section == student.section:
        is_authorized = True
        
    if not is_authorized:
        flash('You are not authorized to manage this permission', 'danger')
        return redirect(url_for('faculty_dashboard'))
    
    if action == 'approve':
        permission.status = 'approved'
        permission.approved_by = current_user.id
        permission.approved_at = datetime.utcnow()
        flash('Permission approved', 'success')
    elif action == 'reject':
        permission.status = 'rejected'
        permission.approved_by = current_user.id
        permission.approved_at = datetime.utcnow()
        flash('Permission rejected', 'warning')
    
    db.session.commit()
    return redirect(url_for('faculty_dashboard'))

# Student Routes
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if not current_user.is_student():
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    events = Event.query.order_by(Event.date.desc()).limit(5).all()
    permissions = Permission.query.filter_by(student_id=current_user.id).order_by(Permission.applied_at.desc()).all()
    
    return render_template('student/dashboard.html', events=events, permissions=permissions)

@app.route('/student/apply-permission', methods=['GET', 'POST'])
@login_required
def apply_permission():
    if not current_user.is_student():
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        date = request.form.get('date')
        club_id = request.form.get('club_id')
        event_id = request.form.get('event_id')
        custom_event = request.form.get('custom_event')
        description = request.form.get('description')
        
        # Handle file upload
        proof_file = request.files.get('proof_file')
        proof_filename = None
        
        if proof_file and allowed_file(proof_file.filename):
            filename = secure_filename(proof_file.filename)
            proof_filename = f"proof_{current_user.roll_no}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename}"
            proof_file.save(os.path.join(app.config['UPLOAD_FOLDER'], proof_filename))
        
        permission = Permission(
            student_id=current_user.id,
            date=datetime.strptime(date, '%Y-%m-%d').date(),
            club_id=club_id,
            event_id=event_id if event_id else None,
            custom_event=custom_event if not event_id else None,
            description=description,
            proof_filename=proof_filename
        )
        
        db.session.add(permission)
        db.session.commit()
        
        flash('Permission application submitted successfully', 'success')
        return redirect(url_for('student_dashboard'))
    
    clubs = Club.query.all()
    events = Event.query.all()
    return render_template('student/apply_permission.html', clubs=clubs, events=events)

@app.route('/student/permissions')
@login_required
def student_permissions():
    if not current_user.is_student():
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    permissions = Permission.query.filter_by(student_id=current_user.id).order_by(Permission.applied_at.desc()).all()
    return render_template('student/permissions.html', permissions=permissions)

@app.route('/student/permission/<int:permission_id>')
@login_required
def student_view_permission(permission_id):
    if not current_user.is_student():
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    permission = Permission.query.get_or_404(permission_id)
    # Ensure student can only view their own permissions
    if permission.student_id != current_user.id:
        flash('Access denied', 'danger')
        return redirect(url_for('student_dashboard'))
    
    return render_template('student/permission_details.html', permission=permission)

# API Routes
@app.route('/api/events/<int:club_id>')
@login_required
def get_events(club_id):
    events = Event.query.filter_by(club_id=club_id).all()
    return jsonify([{'id': event.id, 'name': event.name} for event in events])

@app.route('/download-template')
@login_required
def download_template():
    # Create sample template
    import io
    data = {
        'roll_no': ['24N81A6261', '24N81A6262', '24N81A6263'],
        'email': ['student1@college.edu', 'student2@college.edu', 'student3@college.edu'],
        'first_name': ['John', 'Jane', 'Mike'],
        'last_name': ['Doe', 'Smith', 'Johnson'],
        'section': ['A', 'B', 'A'],
        'department': ['CSE', 'CSE', 'ECE']
    }
    df = pd.DataFrame(data)
    
    # Create in-memory file
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Students', index=False)
    output.seek(0)
    
    return send_file(output, download_name='student_template.xlsx', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)