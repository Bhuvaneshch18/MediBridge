from app import app
with app.test_client() as c:
    with c.session_transaction() as sess:
        sess['user_id'] = 1 # Fake login
    
    response = c.post('/assessment/asthma', data={
        'Age': '25',
        'Gender': 'Male',
        'Height': '1.75',
        'Weight': '70',
        'Smoking_Status': 'Never',
        'Family_History': '0',
        'Allergies': 'None',
        'Air_Pollution_Level': 'Low',
        'Physical_Activity_Level': 'Active',
        'Occupation_Type': 'Indoor'
    })
    print("Status code:", response.status_code)
    if response.status_code == 500:
        print(response.data.decode())
