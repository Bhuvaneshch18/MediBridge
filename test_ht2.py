import joblib
import pandas as pd

bundle = joblib.load('hypertension_model_bundle.pkl')
model = bundle['model']
feature_order = bundle['feature_order']

# Typical low risk data (young, healthy BP)
data1 = {
    'age': 25, 'sex': 0, 'BMI': 22.0, 'Resi': 1,
    'SBP': 110, 'DBP': 70, 'Smoking': 3, 'odisease': 2,
    'creantine': 0.8, 'BUN': 12, 'Noofmed': 0
}

# Typical high risk data (old, very high BP)
data2 = {
    'age': 65, 'sex': 1, 'BMI': 32.0, 'Resi': 2,
    'SBP': 180, 'DBP': 110, 'Smoking': 1, 'odisease': 1,
    'creantine': 1.5, 'BUN': 20, 'Noofmed': 3
}

print(model.predict_proba(pd.DataFrame([data1]))[0])
print(model.predict_proba(pd.DataFrame([data2]))[0])
