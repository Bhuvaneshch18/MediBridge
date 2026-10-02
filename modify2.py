import re

replacement = '''<!-- Google OAuth Sign In Button -->
      <div style="margin-bottom: 10px;">
        <a href="{{ url_for('auth.google_login') }}" class="btn-google" style="display: flex; align-items: center; justify-content: center; width: 100%; padding: 11px 16px; border: 1px solid #dadce0; border-radius: 8px; background-color: #ffffff; color: #3c4043; font-weight: 600; font-size: 0.95rem; text-decoration: none; box-shadow: 0 1px 3px rgba(0,0,0,0.08); transition: background-color 0.2s, box-shadow 0.2s;">
          <svg style="width: 20px; height: 20px; margin-right: 12px;" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
          </svg>
          Continue with Google
        </a>
      </div>

      <!-- Guest Login Button -->
      <div style="margin-bottom: 20px;">
        <a href="{{ url_for('auth.guest_login') }}" class="btn-guest" style="display: flex; align-items: center; justify-content: center; width: 100%; padding: 11px 16px; border: 1px solid #dadce0; border-radius: 8px; background-color: #f8f9fa; color: #3c4043; font-weight: 600; font-size: 0.95rem; text-decoration: none; box-shadow: 0 1px 3px rgba(0,0,0,0.08); transition: background-color 0.2s, box-shadow 0.2s;">
          <svg style="width: 20px; height: 20px; margin-right: 12px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
          Continue as Guest
        </a>
      </div>'''

pattern = re.compile(r'<!-- Google OAuth Sign In Button -->.*?</div>', re.DOTALL)

for filename in ['auth/templates/auth/login.html', 'auth/templates/auth/register.html']:
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = pattern.sub(replacement, content, count=1)
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)
