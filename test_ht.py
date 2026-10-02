import joblib
import pandas as pd
import random

bundle = joblib.load('hypertension_model_bundle.pkl')
model = bundle['model']
feature_order = bundle['feature_order']
mapping = bundle['stage_mapping']

print("Features:", feature_order)

for i in range(5):
    # generate random data
    data = {
        'age': random.randint(30, 80),
        'sex': random.choice([0, 1]),
        'BMI': random.uniform(18.5, 35.0),
        'Resi': random.choice([1, 2]),
        'SBP': random.randint(120, 200),
        'DBP': random.randint(80, 120),
        'Smoking': random.choice([1, 2, 3]),
        'odisease': random.choice([1, 2]),
        'creantine': random.uniform(0.5, 1.5),
        'BUN': random.uniform(10, 20),
        'Noofmed': random.randint(0, 5)
    }
    df = pd.DataFrame([data])
    proba = model.predict_proba(df)[0]
    pred = model.predict(df)[0]
    print(f"Data {i}: Pred={mapping[pred]}, Proba={proba}, Max={max(proba)*100}%")
