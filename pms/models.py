from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.String(20), unique=True, nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    role = db.Column(db.String(20), nullable=False)  # admin, hod, faculty, student
    department = db.Column(db.String(100))
    section = db.Column(db.String(10))
    phone = db.Column(db.String(15))
    is_verified = db.Column(db.Boolean, default=False)
    otp = db.Column(db.String(6))
    otp_expiry = db.Column(db.DateTime)
    is_blocked = db.Column(db.Boolean, default=False)
    
    # Class Incharge Fields
    incharge_department = db.Column(db.String(50)) # e.g., 'CSE'
    incharge_section = db.Column(db.String(10))    # e.g., 'A'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships - specify foreign keys explicitly
    permissions = db.relationship('Permission', backref='student_ref', lazy=True, foreign_keys='Permission.student_id')
    approved_permissions = db.relationship('Permission', backref='approver_ref', lazy=True, foreign_keys='Permission.approved_by')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def validate_roll_no(self):
        if not self.roll_no:
            return False
        pattern = r'^\d{2}[A-Z]\d{2}[A-Z]\d{4}$'
        return re.match(pattern, self.roll_no) is not None
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_hod(self):
        return self.role == 'hod'
    
    def is_faculty(self):
        return self.role in ['faculty', 'hod']

    def is_incharge(self):
        return self.role == 'faculty' and self.incharge_department and self.incharge_section
    
    def is_student(self):
        return self.role == 'student'
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Department {self.name}>'

class SystemConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<SystemConfig {self.key}: {self.value}>'

class Club(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    coordinator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    coordinator = db.relationship('User', backref='clubs_coordinated')
    events = db.relationship('Event', backref='club', lazy=True)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('club.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False)
    venue = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey('club.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=True)
    custom_event = db.Column(db.String(200))
    description = db.Column(db.Text, nullable=False)
    proof_filename = db.Column(db.String(255))
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    
    # Explicit relationships with foreign keys
    club = db.relationship('Club', backref='permissions')
    event = db.relationship('Event', backref='permissions')
    
    # Properties to access student and approver with clear names
    @property
    def student(self):
        return User.query.get(self.student_id)
    
    @property
    def approver(self):
        return User.query.get(self.approved_by) if self.approved_by else None