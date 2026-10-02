with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    \"raise inner_e\",
    \"raise Exception(f'All {len(available_keys)} API keys were rejected by Google. Last error: {inner_e}')\"
)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
