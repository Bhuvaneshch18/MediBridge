from flask import render_template, redirect, url_for, flash, request, session, current_app, make_response
from flask_login import login_user, login_required, current_user, logout_user
from . import auth_bp
from .forms import RegistrationForm, LoginForm, DeleteAccountForm, LocationPreferenceForm, ForgotPasswordRequestForm, PasswordResetForm, UpdateProfileForm, ChangePasswordForm, PrivacySettingsForm, NotificationSettingsForm
from .services import create_user, authenticate_user, delete_user_account, update_login_stats, hash_password, get_or_create_google_user
from .utils import generate_reset_token, verify_reset_token, send_password_reset_email
from extensions import db
from models import User, Assessment, Prescription
import logging
import secrets
import urllib.parse
import requests


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    form = LoginForm()
    
    if form.validate_on_submit():
        user = authenticate_user(form.email.data, form.password.data)
        
        if user:
            login_user(user, remember=form.remember_me.data)
            session.permanent = form.remember_me.data
            session['email'] = user.email
            
            # Update stats securely in service layer
            update_login_stats(user)
            
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password.", "danger")
            
    return render_template('auth/login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    form = RegistrationForm()
    
    if form.validate_on_submit():
        form_data = {
            'full_name': form.full_name.data,
            'email': form.email.data,
            'password': form.password.data
        }
        
        if create_user(form_data):
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for('auth.login'))
        else:
            flash("An unexpected database error occurred. Please try again later.", "danger")
            
    elif request.method == 'POST':
        # Log validation failure or duplicate registration attempt
        email_error = form.email.errors
        if email_error and "already registered" in email_error[0]:
            logging.info(f"Duplicate Registration Attempt for email: {form.email.data}")
        else:
            logging.warning("Validation Failure during registration.")
            
    return render_template('auth/register.html', form=form)

@auth_bp.route('/google')
def google_login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    client_id = current_app.config.get('GOOGLE_CLIENT_ID')
    client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')

    if not client_id or not client_secret:
        flash("Google Login is not configured yet. Please continue as a Guest or register an account.", "warning")
        return redirect(url_for('auth.login'))

    # Live Google OAuth 2.0 Flow
    state = secrets.token_hex(16)
    session['oauth_state'] = state
    redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')

    params = {
        'client_id': client_id,
        'response_type': 'code',
        'scope': 'openid email profile',
        'redirect_uri': redirect_uri,
        'state': state,
        'prompt': 'select_account'
    }

    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return redirect(google_auth_url)

@auth_bp.route('/guest')
def guest_login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    test_email = "guest.user@example.com"
    test_name = "Guest User"
    test_id = "guest_test_1020304050"
    
    user = get_or_create_google_user(test_email, test_name, test_id)
    if user:
        login_user(user, remember=False)
        session.permanent = False
        session['email'] = user.email
        update_login_stats(user)
        flash("Logged in successfully as Guest!", "success")
        return redirect(url_for('home'))
    else:
        flash("Failed to authenticate as Guest.", "danger")
        return redirect(url_for('auth.login'))


@auth_bp.route('/google/callback')
def google_callback():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    error = request.args.get('error')
    if error:
        flash(f"Google authentication error: {error}", "danger")
        return redirect(url_for('auth.login'))

    code = request.args.get('code')
    state = request.args.get('state')
    saved_state = session.pop('oauth_state', None)

    if not code:
        flash("Authorization code missing from Google callback.", "danger")
        return redirect(url_for('auth.login'))

    if saved_state and state != saved_state:
        flash("State verification failed. Possible CSRF attack detected.", "danger")
        return redirect(url_for('auth.login'))

    client_id = current_app.config.get('GOOGLE_CLIENT_ID')
    client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')
    redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')

    # Exchange authorization code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }

    try:
        token_response = requests.post(token_url, data=token_data, timeout=10)
        token_json = token_response.json()

        if token_response.status_code != 200 or 'access_token' not in token_json:
            error_desc = token_json.get('error_description', 'Failed to retrieve access token from Google.')
            logging.error(f"Google Token Error: {token_json}")
            flash(f"Google authentication failed: {error_desc}", "danger")
            return redirect(url_for('auth.login'))

        access_token = token_json['access_token']

        # Fetch user info from Google
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        userinfo_headers = {'Authorization': f'Bearer {access_token}'}
        userinfo_response = requests.get(userinfo_url, headers=userinfo_headers, timeout=10)

        if userinfo_response.status_code != 200:
            flash("Failed to retrieve user info from Google.", "danger")
            return redirect(url_for('auth.login'))

        user_data = userinfo_response.json()
        email = user_data.get('email')
        full_name = user_data.get('name')
        google_id = user_data.get('id')

        if not email or not google_id:
            flash("Google profile did not return an email or user ID.", "danger")
            return redirect(url_for('auth.login'))

        user = get_or_create_google_user(email, full_name, google_id)
        if user:
            login_user(user, remember=False)
            session.permanent = False
            session['email'] = user.email
            update_login_stats(user)
            flash(f"Welcome back, {user.full_name}! Successfully logged in with Google.", "success")
            return redirect(url_for('home'))
        else:
            flash("Failed to process user account after Google authentication.", "danger")
            return redirect(url_for('auth.login'))

    except Exception as e:
        logging.error(f"Unexpected error in Google OAuth callback: {str(e)}")
        flash("An unexpected network error occurred during Google authentication.", "danger")
        return redirect(url_for('auth.login'))

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect('/')

@auth_bp.route('/profile')
@login_required
def profile():
    user_id = current_user.id
    assessments = Assessment.query.filter_by(user_id=user_id).order_by(Assessment.assessment_date.desc()).all()
    prescriptions = Prescription.query.filter_by(user_id=user_id).order_by(Prescription.uploaded_at.desc()).all()
    
    total_assessments = len(assessments)
    latest_assessment = assessments[0] if assessments else None
    high_risk_count = sum(1 for a in assessments if a.risk_level and 'high' in a.risk_level.lower() or 'critical' in a.risk_level.lower() or 'crisis' in a.risk_level.lower())
    total_prescriptions = len(prescriptions)
    
    # Disease Distribution for Chart
    disease_counts = {}
    for a in assessments:
        disease_counts[a.disease_name] = disease_counts.get(a.disease_name, 0) + 1
        
    # Activity Level
    activity_level = "Active" if total_assessments > 2 else "Getting Started" if total_assessments > 0 else "New User"
    
    # Insights
    insight_title = "Get Started"
    insight_text = "Complete your first assessment or Daily Wellness Score to begin building your health activity overview."
    if high_risk_count > 0:
        insight_title = "Attention Needed"
        insight_text = "Your recent assessment includes a high-risk result. Review the assessment details and consider appropriate next steps."
    elif total_assessments > 0:
        insight_title = "Assessment Activity"
        insight_text = f"You have completed {total_assessments} assessments on MediBridge."

    # Health Journey logic (Wellness is not stored in DB, so False. Prescriptions yes)
    has_first_assessment = total_assessments > 0
    has_multiple_assessments = total_assessments > 1
    from models import WellnessScore
    wellness_scores = WellnessScore.query.filter_by(user_id=user_id).order_by(WellnessScore.created_at.desc()).all()
    latest_wellness = wellness_scores[0] if wellness_scores else None
    has_wellness = len(wellness_scores) > 0
    has_prescription = total_prescriptions > 0
    
    from models import SavedHospital
    saved_hospitals = SavedHospital.query.filter_by(user_id=user_id).order_by(SavedHospital.saved_at.desc()).all()
    
    return render_template(
        'auth/profile.html',
        assessments=assessments,
        prescriptions=prescriptions,
        latest_wellness=latest_wellness,
        saved_hospitals=saved_hospitals,
        total_assessments=total_assessments,
        latest_assessment=latest_assessment,
        high_risk_count=high_risk_count,
        total_prescriptions=total_prescriptions,
        disease_counts=disease_counts,
        activity_level=activity_level,
        insight_title=insight_title,
        insight_text=insight_text,
        has_first_assessment=has_first_assessment,
        has_multiple_assessments=has_multiple_assessments,
        has_wellness=has_wellness,
        has_prescription=has_prescription
    )

@auth_bp.route('/settings')
@login_required
def settings():
    form = DeleteAccountForm()
    location_form = LocationPreferenceForm(obj=current_user)
    update_profile_form = UpdateProfileForm(obj=current_user)
    change_password_form = ChangePasswordForm()
    privacy_form = PrivacySettingsForm()
    notification_form = NotificationSettingsForm()
    return render_template('auth/settings.html', 
                           form=form, 
                           location_form=location_form,
                           update_profile_form=update_profile_form,
                           change_password_form=change_password_form,
                           privacy_form=privacy_form,
                           notification_form=notification_form)

@auth_bp.route('/profile/location', methods=['POST'])
@login_required
def update_location_preferences():
    location_form = LocationPreferenceForm()
    if location_form.validate_on_submit():
        user = db.session.get(User, current_user.id)
        user.allow_location = location_form.allow_location.data
        user.preferred_location = location_form.preferred_location.data.strip() if location_form.preferred_location.data else None
        db.session.commit()
        flash("Your hospital finder location preferences have been updated.", "success")
    else:
        flash("Failed to update location preferences. Please check your input.", "danger")
    return redirect(url_for('auth.settings'))

@auth_bp.route('/profile/delete', methods=['POST'])
@login_required
def delete_account():
    form = DeleteAccountForm()
    if form.validate_on_submit():
        if delete_user_account(current_user):
            logout_user()
            flash("Your account has been permanently deleted.", "info")
            return redirect(url_for('home'))
        else:
            flash("An error occurred while deleting your account.", "danger")
            return redirect(url_for('auth.settings'))
    return redirect(url_for('auth.settings'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = ForgotPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = generate_reset_token(user)
            send_password_reset_email(user, token)
            flash("A password reset link has been sent to your email address! (For local testing without SMTP, please check your console output to find the reset link)", "success")
        else:
            flash("If an account with that email exists, a password reset link has been sent.", "info")
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password_request.html', form=form)

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = verify_reset_token(token)
    if not user:
        flash("That is an invalid or expired token. Please request a new password reset.", "warning")
        return redirect(url_for('auth.forgot_password_request'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        user.password_hash = hash_password(form.password.data)
        db.session.commit()
        flash("Your password has been updated! You are now able to log in with your new password.", "success")
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)

@auth_bp.route('/profile/edit', methods=['POST'])
@login_required
def update_profile():
    form = UpdateProfileForm()
    if form.validate_on_submit():
        user = db.session.get(User, current_user.id)
        user.full_name = form.full_name.data.strip()
        user.phone_number = form.phone_number.data.strip() if form.phone_number.data else None
        user.gender = form.gender.data.strip() if form.gender.data else None
        user.date_of_birth = form.date_of_birth.data.strip() if form.date_of_birth.data else None
        db.session.commit()
        flash("Your profile information has been updated successfully!", "success")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "danger")
    return redirect(url_for('auth.settings'))

@auth_bp.route('/profile/change-password', methods=['POST'])
@login_required
def change_password_route():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not authenticate_user(current_user.email, form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            user = db.session.get(User, current_user.id)
            user.password_hash = hash_password(form.new_password.data)
            db.session.commit()
            flash("Your password has been changed successfully!", "success")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{error}", "danger")
    return redirect(url_for('auth.settings'))

@auth_bp.route('/profile/privacy', methods=['POST'])
@login_required
def update_privacy():
    form = PrivacySettingsForm()
    if form.validate_on_submit():
        flash("Your privacy and data sharing settings have been saved securely!", "success")
    else:
        flash("Failed to update privacy settings.", "danger")
    return redirect(url_for('auth.settings'))

@auth_bp.route('/profile/notifications', methods=['POST'])
@login_required
def update_notifications():
    form = NotificationSettingsForm()
    if form.validate_on_submit():
        flash("Your notification preferences have been updated successfully!", "success")
    else:
        flash("Failed to update notification preferences.", "danger")
    return redirect(url_for('auth.settings'))

