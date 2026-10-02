with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'is_rate_limit = "429" in error_msg or "resourceexhausted" in error_msg or "quota" in error_msg',
    'is_rate_limit = "429" in error_msg or "resourceexhausted" in error_msg or "quota" in error_msg or "403" in error_msg or "permission" in error_msg or "400" in error_msg'
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
