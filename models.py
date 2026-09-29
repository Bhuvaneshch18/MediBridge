from extensions import db, login_manager
from flask_login import UserMixin
from datetime import datetime, timezone

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(20), nullable=True)
    date_of_birth = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    login_count = db.Column(db.Integer, default=0, server_default='0', nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    allow_location = db.Column(db.Boolean, default=False, server_default='0', nullable=False)
    preferred_location = db.Column(db.String(100), nullable=True)
    has_rated = db.Column(db.Boolean, default=False, server_default='0', nullable=False)
    rating_value = db.Column(db.Integer, nullable=True)

    # Relationships
    assessments = db.relationship('Assessment', backref='user', lazy=True, cascade="all, delete-orphan")
    prescriptions = db.relationship('Prescription', backref='user', lazy=True, cascade="all, delete-orphan")
    wellness_scores = db.relationship('WellnessScore', backref='user', lazy=True, cascade="all, delete-orphan")
    saved_hospitals = db.relationship('SavedHospital', backref='user', lazy=True, cascade="all, delete-orphan")

    # ==========================================
    # BACKWARD COMPATIBILITY PROPERTIES
    # These properties map the old dummy fields 
    # to the new schema to prevent app.py from crashing.
    # ==========================================
    @property
    def name(self):
        return self.full_name

    @name.setter
    def name(self, value):
        self.full_name = value

    @property
    def password(self):
        return self.password_hash

    @password.setter
    def password(self, value):
        self.password_hash = value

    @property
    def phone(self):
        return self.phone_number

    @phone.setter
    def phone(self, value):
        self.phone_number = value

    @property
    def age(self):
        return None  # Replaced by date_of_birth in the future

    @property
    def blood_group(self):
        return None  # Obsolete field

class Assessment(db.Model):
    __tablename__ = 'assessments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    disease_name = db.Column(db.String(100), nullable=False)
    risk_level = db.Column(db.String(50), nullable=False, default="Pending ML")
    risk_score = db.Column(db.Float, nullable=True, default=0.0)
    status = db.Column(db.String(50), default="Completed")
    assessment_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    responses = db.relationship('QuestionnaireResponse', backref='assessment', lazy=True, cascade="all, delete-orphan")

class QuestionnaireResponse(db.Model):
    __tablename__ = 'questionnaire_responses'

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)

class Prescription(db.Model):
    __tablename__ = 'prescriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ai_summary = db.Column(db.Text, nullable=True)

class WellnessScore(db.Model):
    __tablename__ = 'wellness_scores'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class SavedHospital(db.Model):
    __tablename__ = 'saved_hospitals'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    hospital_name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(500), nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lon = db.Column(db.Float, nullable=True)
    saved_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
