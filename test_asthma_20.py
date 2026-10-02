import joblib
import numpy as np
import os
import sys

sys.path.append(os.getcwd())
from asthma_service import predict_asthma

bundle = joblib.load('asthma_model_bundle.pkl')
import asthma_service
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

found = False
for smoke in ['Never', 'Former', 'Current']:
    for allergy in ['None', 'Dust', 'Pets', 'Pollen', 'Multiple']:
        for hist in ['0', '1']:
            for air in ['Low', 'Moderate', 'High']:
                asthma_data['Smoking_Status'] = smoke
                asthma_data['Allergies'] = allergy
                asthma_data['Family_History'] = hist
                asthma_data['Air_Pollution_Level'] = air
                res = predict_asthma(asthma_data)
                if 10 <= res['probability'] <= 35:
                    print(f"Prob {res['probability']}% | Data: {asthma_data}")
                    found = True
                    if res['probability'] >= 15:
                        sys.exit(0)
