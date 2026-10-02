import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add capping logic for heart and diabetes in app.py
old_prob_code = '''pos_prob = proba[pos_idx]
                prob_pct = int(pos_prob * 100)
                model_name_str = "KNN (K-Nearest Neighbors)"'''

new_prob_code = '''pos_prob = proba[pos_idx]
                prob_pct = int(pos_prob * 100)
                if prob_pct > 95:
                    prob_pct = 95
                elif prob_pct < 5:
                    prob_pct = 5
                model_name_str = "KNN (K-Nearest Neighbors)"'''

content = content.replace(old_prob_code, new_prob_code)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("app.py modified")
