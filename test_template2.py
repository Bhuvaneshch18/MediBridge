from flask import Flask, render_template
app = Flask(__name__, template_folder='templates')

class DummyUser:
    is_authenticated = True
    name = "Test User"
    
@app.context_processor
def inject_user():
    return dict(current_user=DummyUser())

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
            'BMI': 22.5,
            'Peak_Expiratory_Flow': '500',
            'FeNO_Level': '15'
        }
    }
    return render_template('asthma_result.html', result=result, title='Asthma Risk Assessment')

with app.test_request_context('/'):
    test()
    print("SUCCESS RENDER!")
