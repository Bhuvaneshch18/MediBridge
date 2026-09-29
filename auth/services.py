from extensions import db, bcrypt
from models import User
import logging
from datetime import datetime, timezone

def hash_password(password):
    """Securely hashes the password using Flask-Bcrypt."""
    return bcrypt.generate_password_hash(password).decode('utf-8')

def create_user(form_data):
    """
    Creates a new user in the PostgreSQL database.
    Expects form_data dictionary with 'full_name', 'email', and 'password'.
    """
    try:
        email = form_data['email'].lower()
        hashed_pwd = hash_password(form_data['password'])
        
        new_user = User(
            full_name=form_data['full_name'],
            email=email,
            password_hash=hashed_pwd
        )
        
        db.session.add(new_user)
        db.session.commit()
        logging.info(f"Successful registration for email: {email}")
        return True
    except Exception as e:
        db.session.rollback()
        logging.error(f"Unexpected Database Error during registration for email {form_data.get('email')}: {str(e)}")
        return False

def authenticate_user(email, password):
    """
    Authenticates a user by email and password securely.
    Returns the User object if successful, None otherwise.
    """
    try:
        user = User.query.filter_by(email=email.lower()).first()
        if user and verify_password(user.password_hash, password):
            logging.info(f"Successful Login for email: {email.lower()}")
            return user
        
        logging.warning(f"Failed Login attempt for email: {email.lower()}")
        return None
    except Exception as e:
        logging.error(f"Unexpected Error during login for email {email}: {str(e)}")
        return None

def update_login_stats(user):
    """Updates the user's login count and last login timestamp."""
    try:
        user.login_count += 1
        user.last_login = datetime.now(timezone.utc)
        db.session.commit()
        logging.info(f"Login stats updated for user: {user.email}")
        return True
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating login stats for user {user.email}: {str(e)}")
        return False

def logout_user_service():
    # Placeholder for logout service
    pass

def verify_password(hashed_password, password):
    """Securely verifies the plain text password against the hashed password."""
    try:
        if hashed_password.startswith('pbkdf2:') or hashed_password.startswith('scrypt:'):
            from werkzeug.security import check_password_hash as werkzeug_check
            return werkzeug_check(hashed_password, password)
        return bcrypt.check_password_hash(hashed_password, password)
    except Exception as e:
        logging.error(f"Password verification error: {str(e)}")
        return False

def delete_user_account(user):
    """Safely deletes a user from the database."""
    try:
        db.session.delete(user)
        db.session.commit()
        logging.info(f"User account deleted permanently for: {user.email}")
        return True
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting user account {user.email}: {str(e)}")
        return False

def get_or_create_google_user(email, full_name, google_id):
    """
    Finds existing user by email or google_id, or creates a new user for Google OAuth login.
    Returns the User object or None if an error occurred.
    """
    try:
        clean_email = email.lower().strip()
        user = User.query.filter((User.google_id == google_id) | (User.email == clean_email)).first()

        if user:
            if not user.google_id and google_id:
                user.google_id = google_id
                db.session.commit()
            logging.info(f"Existing user retrieved for Google login: {clean_email}")
            return user
        
        # Create new Google user
        new_user = User(
            full_name=full_name or clean_email.split('@')[0].title(),
            email=clean_email,
            google_id=google_id
        )
        db.session.add(new_user)
        db.session.commit()
        logging.info(f"New user created via Google OAuth: {clean_email}")
        return new_user
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error in get_or_create_google_user for {email}: {str(e)}")
        return None
