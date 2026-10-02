import glob
files = ['app.py', 'hypertension_service.py', 'obesity_service.py', 'asthma_service.py']
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Simple replacement to remove the block
    content = content.replace("        if prob_pct > 95:\n            prob_pct = 95\n        elif prob_pct < 5:\n            prob_pct = 5\n", "")
    content = content.replace("                if prob_pct > 95:\n                    prob_pct = 95\n                elif prob_pct < 5:\n                    prob_pct = 5\n", "")
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
print("Removed caps.")
