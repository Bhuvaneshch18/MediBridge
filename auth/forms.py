from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo
from .validators import check_duplicate_email, validate_password_strength, validate_full_name

class RegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[
        DataRequired(message="Full Name is required."),
        Length(min=3, max=100, message="Full Name must be between 3 and 100 characters."),
        validate_full_name
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Invalid email format."),
        check_duplicate_email
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required."),
        validate_password_strength
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo('password', message="Passwords must match.")
    ])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Invalid email format.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required.")
    ])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class DeleteAccountForm(FlaskForm):
    submit = SubmitField('Delete Account Permanently')

class LocationPreferenceForm(FlaskForm):
    allow_location = BooleanField('Allow Location Access for Hospital Finder')
    preferred_location = StringField('Default Preferred City / Pincode', validators=[Length(max=100)])
    submit = SubmitField('Save Location Preferences')

class ForgotPasswordRequestForm(FlaskForm):
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Invalid email format.")
    ])
    submit = SubmitField('Request Password Reset')

class PasswordResetForm(FlaskForm):
    password = PasswordField('New Password', validators=[
        DataRequired(message="Password is required."),
        validate_password_strength
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo('password', message="Passwords must match.")
    ])
    submit = SubmitField('Reset Password')

class UpdateProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    phone_number = StringField('Phone Number', validators=[Length(max=20)])
    gender = StringField('Gender', validators=[Length(max=20)])
    date_of_birth = StringField('Date of Birth', validators=[Length(max=20)])
    submit = SubmitField('Save Profile Changes')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), validate_password_strength])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password', message='New passwords must match.')])
    submit = SubmitField('Update Password')

class PrivacySettingsForm(FlaskForm):
    research_sharing = BooleanField('Allow anonymized data for ML research')
    ai_insights = BooleanField('Enable AI-driven health insights personalization')
    profile_visibility = StringField('Profile Visibility')
    submit = SubmitField('Save Privacy Settings')

class NotificationSettingsForm(FlaskForm):
    email_alerts = BooleanField('Email alerts for completed assessments')
    weekly_digest = BooleanField('Weekly health summary digest')
    security_alerts = BooleanField('New device login security alerts')
    hospital_alerts = BooleanField('New nearby hospital recommendations')
    submit = SubmitField('Save Notification Preferences')

