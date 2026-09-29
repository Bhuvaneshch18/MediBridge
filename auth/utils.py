import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask import current_app, url_for
from extensions import db
from models import User

def generate_reset_token(user):
    """
    Generates a secure, time-limited cryptographic token for password reset.
    The token encodes the user's ID and is signed with the app's SECRET_KEY.
    """
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps({'user_id': user.id}, salt='password-reset-salt')

def verify_reset_token(token, expires_sec=3600):
    """
    Verifies a password reset token. Returns the User object if valid and not expired,
    or None otherwise. Default expiry is 1 hour (3600 seconds).
    """
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        data = s.loads(token, salt='password-reset-salt', max_age=expires_sec)
        user_id = data.get('user_id')
        if not user_id:
            return None
        return db.session.get(User, int(user_id))
    except (SignatureExpired, BadSignature, Exception) as e:
        logging.warning(f"Failed or expired token verification attempt: {str(e)}")
        return None

def send_password_reset_email(user, token):
    """
    Constructs the password reset URL and sends an email to the user.
    Also logs the reset URL to the console for local debugging and dev testing without SMTP.
    """
    reset_url = url_for('auth.reset_password', token=token, _external=True)
    
    # 1. Always log cleanly to console for local developer testing
    print("\n" + "="*70)
    print(" 📧 MEDIBRIDGE PASSWORD RESET EMAIL (LOCAL DEV SIMULATION) ")
    print("="*70)
    print(f"To: {user.full_name} <{user.email}>")
    print(f"Subject: Reset Your MediBridge Password")
    print("-" * 70)
    print("Hello,")
    print(f"You recently requested to reset your password for your MediBridge account.")
    print("To reset your password, please click the link below (valid for 1 hour):")
    print(f"\n👉 {reset_url}\n")
    print("If you did not request a password reset, please ignore this email.")
    print("="*70 + "\n")
    logging.info(f"Password reset link generated for {user.email}: {reset_url}")

    # 2. Try sending via SMTP if configured in environment variables
    mail_server = current_app.config.get('MAIL_SERVER') or current_app.config.get('SMTP_SERVER')
    mail_port = current_app.config.get('MAIL_PORT', 587)
    mail_user = current_app.config.get('MAIL_USERNAME') or current_app.config.get('SMTP_USERNAME')
    mail_pass = current_app.config.get('MAIL_PASSWORD') or current_app.config.get('SMTP_PASSWORD')

    if mail_server and mail_user and mail_pass:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "Reset Your MediBridge Password"
            msg['From'] = mail_user
            msg['To'] = user.email

            text_body = f"""Hello {user.full_name},\n\nYou requested to reset your password for MediBridge.\nPlease click the link below to reset your password:\n{reset_url}\n\nIf you did not request this, please ignore this email.\n"""
            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                  <h2 style="color: #0284c7;">MediBridge Password Reset</h2>
                  <p>Hello <strong>{user.full_name}</strong>,</p>
                  <p>You recently requested to reset your password for your MediBridge account. Click the button below to set a new password:</p>
                  <p style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" style="background-color: #0284c7; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Reset Password</a>
                  </p>
                  <p style="font-size: 0.9em; color: #666;">Or copy and paste this link into your browser:<br><a href="{reset_url}">{reset_url}</a></p>
                  <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                  <p style="font-size: 0.8em; color: #999;">If you did not request a password reset, please ignore this email or contact support if you have concerns.</p>
                </div>
              </body>
            </html>
            """

            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))

            with smtplib.SMTP(mail_server, int(mail_port)) as server:
                server.starttls()
                server.login(mail_user, mail_pass)
                server.send_message(msg)
            logging.info(f"SMTP email successfully sent to {user.email}")
            return True
        except Exception as e:
            logging.error(f"Failed to send SMTP email to {user.email}: {str(e)}")
            return False
    else:
        logging.info("SMTP environment variables not configured; relying on console/UI debug mode for email link delivery.")
        return True
