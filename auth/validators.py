import re
from wtforms.validators import ValidationError
from models import User

def check_duplicate_email(_form, field):
    """Checks if the email is already registered in the database."""
    email = field.data.lower()
    user = User.query.filter_by(email=email).first()
    if user:
        raise ValidationError("This email is already registered.")

def validate_full_name(_form, field):
    """Validates that the full name only contains letters and spaces."""
    name = field.data
    if not re.match(r"^[A-Za-z\s]+$", name):
        raise ValidationError("Full name can only contain letters and spaces.")

def validate_password_strength(_form, field):
    """Validates that password meets security requirements."""
    password = field.data
    
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if not re.search(r"[a-z]", password):
        raise ValidationError("Password must contain at least one lowercase letter.")
    if not re.search(r"[A-Z]", password):
        raise ValidationError("Password must contain at least one uppercase letter.")
    if not re.search(r"[0-9]", password):
        raise ValidationError("Password must contain at least one number.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise ValidationError("Password must contain at least one special character.")
