import joblib
import os
import sys

sys.path.append(os.getcwd())

bundle = joblib.load('asthma_model_bundle.pkl')
print(bundle.get('feature_order'))
