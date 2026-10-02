with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    \"['GEMINI_API_KEY', 'GEMINI_API_KEY_1', 'GEMINI_API_KEY_2', 'GEMINI_API_KEY_3', 'GEMINI_API_KEY_4', 'GEMINI_API_KEY_5']\",
    \"['GEMINI_API_KEY_1', 'GEMINI_API_KEY_2', 'GEMINI_API_KEY_3']\"
)

# And fix the fallback:
content = content.replace(
    \"available_keys = [os.getenv('GEMINI_API_KEY')]\",
    \"available_keys = [os.getenv('GEMINI_API_KEY_1')]\"
)

# And fix the initial client fallback
content = content.replace(
    \"current_client = client if available_keys[0] == os.getenv('GEMINI_API_KEY') else genai.Client(api_key=available_keys[0])\",
    \"current_client = genai.Client(api_key=available_keys[0])\"
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
