with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix chat endpoint
content = content.replace(
    \"\"\"        if not available_keys:
            available_keys = [os.getenv('GEMINI_API_KEY_1')]
            
        max_retries = len(available_keys) + 2
        current_key_idx = 0
        current_client = genai.Client(api_key=available_keys[0])\"\"\",
    \"\"\"        if not available_keys:
            raise ValueError(\"Zero API keys found. GEMINI_API_KEY_1 is missing or not configured for Production.\")
            
        max_retries = len(available_keys) + 2
        current_key_idx = 0
        # Prevent SDK from secretly falling back to broken GEMINI_API_KEY
        if 'GEMINI_API_KEY' in os.environ:
            del os.environ['GEMINI_API_KEY']
        current_client = genai.Client(api_key=available_keys[0])\"\"\"
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
