with open('asthma_service.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_prob = '''        prediction_num = _asthma_model.predict(input_df)[0]
        proba = _asthma_model.predict_proba(input_df)[0]
        prob_pct = int(max(proba) * 100)'''

new_prob = '''        prediction_num = _asthma_model.predict(input_df)[0]
        proba = _asthma_model.predict_proba(input_df)[0]
        
        # Always use the probability of the positive class (Asthma = index 1)
        # Assuming classes are ordered [0, 1] for binary
        if len(proba) > 1:
            pos_prob = proba[1]
        else:
            pos_prob = proba[0]
            
        prob_pct = int(pos_prob * 100)'''

content = content.replace(old_prob, new_prob)

with open('asthma_service.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Modified asthma_service.py")
