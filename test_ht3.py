import joblib
import pandas as pd
bundle = joblib.load('hypertension_model_bundle.pkl')
model = bundle['model']
data = {'age': 45, 'sex': 0, 'BMI': 25.0, 'Resi': 1, 'SBP': 120, 'DBP': 80, 'Smoking': 3, 'odisease': 2, 'creantine': 0.9, 'BUN': 15, 'Noofmed': 0}
print(model.predict_proba(pd.DataFrame([data]))[0])
