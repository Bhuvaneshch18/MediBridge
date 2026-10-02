import joblib
import os
import sys

sys.path.append(os.getcwd())
from asthma_service import predict_asthma
import asthma_service

bundle = joblib.load('asthma_model_bundle.pkl')
asthma_service._asthma_model = bundle.get('model')
asthma_service._asthma_feature_order = bundle.get('feature_order')
asthma_service._asthma_label_mapping = bundle.get('label_mapping')
asthma_service._asthma_encoders = bundle.get('encoders')

asthma_data = {
    'Age': 25,
    'Gender': 'Male',
    'Height': 1.75,
    'Weight': 70,
    'Smoking_Status': 'Never',
    'Family_History': '0',
    'Allergies': 'None',
    'Air_Pollution_Level': 'Low',
    'Physical_Activity_Level': 'Active',
    'Occupation_Type': 'Indoor'
}
try:
    res = predict_asthma(asthma_data)
    print(res)
except Exception as e:
    import traceback
    traceback.print_exc()
