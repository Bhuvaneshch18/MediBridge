import re

with open('auth/routes.py', 'r') as f:
    content = f.read()

replacement = \"\"\"@auth_bp.route('/google')
def google_login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    client_id = current_app.config.get('GOOGLE_CLIENT_ID')
    client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')

    if not client_id or not client_secret:
        flash("Google Login is not configured yet. Please continue as a Guest or register an account.", "warning")
        return redirect(url_for('auth.login'))

    state = secrets.token_hex(16)
    session['oauth_state'] = state
    redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')
    auth_url = (f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=openid%20email%20profile&state={state}&access_type=offline&prompt=consent")
    return redirect(auth_url)

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
        return redirect(url_for('auth.login'))\"\"\"

pattern = re.compile(r"@auth_bp\.route\('/google'\).*?return redirect\(auth_url\)", re.DOTALL)
content = pattern.sub(replacement, content)

with open('auth/routes.py', 'w') as f:
    f.write(content)
