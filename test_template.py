from flask import Flask, render_template, session
app = Flask(__name__, template_folder='templates')
app.secret_key = 'test'

@app.route('/')
def test():
    result = {
        'status': 'success',
        'stage': 'No Asthma',
        'riskLevel': 'No Asthma',
        'probability': 15,
        'color': 'green',
        'recommendations': {
            'lifestyle_suggestions': 'test',
            'diet_recommendations': 'test',
            'exercise_recommendations': 'test',
            'hydration_advice': 'test',
            'healthy_weight_tips': 'test'
        },
        'input_data': {
            'Age': '25',
            'BMI': 22.5
        }
    }
    return render_template('asthma_result.html', result=result, title='Asthma Risk Assessment')

with app.test_request_context('/'):
    print(test())
