import json
result = {
    'status': 'success',
    'stage': 'No Asthma',
    'riskLevel': 'No Asthma',
    'probability': 15,
    'color': 'green',
    'recommendations': {
        'lifestyle_suggestions': 'Continue maintaining a healthy lifestyle and avoid smoking and second-hand smoke.',
        'diet_recommendations': 'Maintain a balanced diet rich in antioxidants to support lung health.',
        'exercise_recommendations': 'Exercise regularly to keep your cardiovascular system strong.',
        'hydration_advice': 'Drink plenty of water to keep your respiratory tract hydrated.',
        'healthy_weight_tips': 'Schedule regular health check-ups if symptoms develop.'
    },
    'input_data': {
        'Age': '25',
        'Gender': 'Male',
        'Height': '1.75',
        'Weight': '70',
        'Smoking_Status': 'Never',
        'Family_History': '0',
        'Allergies': 'None',
        'Air_Pollution_Level': 'Low',
        'Physical_Activity_Level': 'Active',
        'Occupation_Type': 'Indoor',
        'Comorbidities': 'None',
        'Medication_Adherence': '5',
        'Number_of_ER_Visits': '0',
        'Peak_Expiratory_Flow': '500',
        'FeNO_Level': '15',
        'BMI': 22.857
    },
    'model_name': "Random Forest Classifier Model (asthma_model.pkl)"
}
from flask.sessions import SecureCookieSessionInterface
from flask import Flask
app = Flask(__name__)
app.secret_key = 'test'
si = SecureCookieSessionInterface()
val = si.get_signing_serializer(app).dumps(dict(assessment_result=result, assessment_title='Asthma Risk Assessment'))
print("Cookie payload size:", len(val))
