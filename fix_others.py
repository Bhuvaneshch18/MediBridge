import os

files_to_fix = ['obesity_service.py', 'hypertension_service.py']
for file in files_to_fix:
    if os.path.exists(file):
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        old_prob = '''        prob_pct = int(max(proba) * 100)'''
        new_prob = '''        prob_pct = int(max(proba) * 100)
        if prob_pct > 95:
            prob_pct = 95
        elif prob_pct < 5:
            prob_pct = 5'''
            
        content = content.replace(old_prob, new_prob)
        
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"{file} modified")
