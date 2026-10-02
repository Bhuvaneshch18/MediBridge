import joblib
import os
import sys

sys.path.append(os.getcwd())
bundle_path = os.path.join(os.getcwd(), 'asthma_model_bundle.pkl')
bundle = joblib.load(bundle_path)
print(bundle.get('label_mapping'))
