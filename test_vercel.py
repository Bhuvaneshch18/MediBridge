import requests
import time
import random

session = requests.Session()
URL = "https://medi-bridge-beige.vercel.app"

email = f"debug_{random.randint(1000,9999)}@example.com"
print("Registering", email)
resp = session.post(f"{URL}/auth/register", data={
    'email': email,
    'password': 'password123',
    'confirm': 'password123',
    'first_name': 'Debug',
    'last_name': 'User'
})
print("Register status:", resp.status_code)

session.post(f"{URL}/auth/login", data={
    'email': email,
    'password': 'password123'
})

data = {
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
    'FeNO_Level': '15'
}

resp = session.post(f"{URL}/assessment/asthma", data=data)
print("Submit status code:", resp.status_code)
if resp.status_code == 500:
    print("GOT 500!")
else:
    print("Redirected to:", resp.url)
