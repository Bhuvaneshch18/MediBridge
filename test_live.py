import os
import requests
from bs4 import BeautifulSoup

# Start local server in background
os.system('set FLASK_ENV=development && start /b python app.py > server.log 2>&1')
import time
time.sleep(5)

# Try login and submit
session = requests.Session()
# Register a dummy user
res = session.post('http://localhost:5000/auth/register', data={
    'email': 'test2@example.com',
    'password': 'password',
    'confirm': 'password',
    'first_name': 'Test',
    'last_name': 'User'
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
resp = session.post('http://localhost:5000/assessment/asthma', data=data)
print("Status Code:", resp.status_code)
if resp.status_code == 500:
    print("500 Error encountered!")
    # read the server log to see traceback
    with open('server.log', 'r') as f:
        print(f.read())
else:
    print("Success. URL:", resp.url)

# Kill server
os.system('taskkill /F /IM python.exe /T')
