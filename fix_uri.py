import re

with open('auth/routes.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all occurrences
content = content.replace(
    \"redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')\",
    \"redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI') or url_for('auth.google_callback', _external=True, _scheme='https')\"
)

# Ensure os is imported if not already
if 'import os' not in content:
    content = 'import os\n' + content

with open('auth/routes.py', 'w', encoding='utf-8') as f:
    f.write(content)
