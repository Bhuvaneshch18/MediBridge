import joblib
import os
import sys

sys.path.append(os.getcwd())
try:
    bundle = joblib.load('hypertension_model_bundle.pkl')
    print("Hypertension labels:", bundle.get('label_mapping'))
except: pass

try:
    bundle = joblib.load('obesity_model_bundle.pkl')
    print("Obesity labels:", bundle.get('label_mapping'))
except: pass
