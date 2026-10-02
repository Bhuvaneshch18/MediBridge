import os
import joblib
import pandas as pd

# Global variables to store bundle contents
_ht_model = None
_ht_feature_order = None
_ht_stage_mapping = None

def init_hypertension_model(app_root_path):
    """
    Loads the hypertension_model_bundle.pkl exactly once at startup.
    """
    global _ht_model, _ht_feature_order, _ht_stage_mapping
    
    bundle_path = os.path.join(app_root_path, 'hypertension_model_bundle.pkl')
    
    try:
        if os.path.exists(bundle_path):
            bundle = joblib.load(bundle_path)
            _ht_model = bundle.get('model')
            _ht_feature_order = bundle.get('feature_order')
            _ht_stage_mapping = bundle.get('stage_mapping')
            print("✓ Hypertension Model Bundle Loaded Successfully")
        else:
            print("! Hypertension model bundle not found. Predictions will fail gracefully.")
    except Exception as e:
        print(f"! Failed to load hypertension model bundle: {e}")

def get_recommendations(stage_name):
    """
    Returns personalized recommendations based on the predicted stage.
    """
    if stage_name == 'Stage 1':
        return {
            'lifestyle_suggestions': 'Monitor blood pressure regularly and limit stress where possible.',
            'diet_recommendations': 'Reduce salt and sodium intake, and maintain a healthy balanced diet.',
            'exercise_recommendations': 'Exercise regularly, aiming for at least 150 minutes of moderate activity per week.',
            'hydration_advice': 'Drink plenty of water and limit alcohol and caffeine consumption.',
            'healthy_weight_tips': 'Maintain a healthy weight, as even a small amount of weight loss can improve blood pressure.'
        }
    elif stage_name == 'Stage 2':
        return {
            'lifestyle_suggestions': 'Consult a healthcare professional to discuss a comprehensive treatment plan.',
            'diet_recommendations': 'Strictly reduce sodium intake and consider the DASH (Dietary Approaches to Stop Hypertension) diet.',
            'exercise_recommendations': 'Increase physical activity as approved by your doctor.',
            'hydration_advice': 'Avoid sugary drinks and stay hydrated with water throughout the day.',
            'healthy_weight_tips': 'Monitor your weight regularly and focus on long-term sustainable habits.'
        }
    elif stage_name == 'Hypertensive Crisis':
        return {
            'lifestyle_suggestions': 'Seek immediate medical attention and do not ignore symptoms.',
            'diet_recommendations': 'Follow emergency medical advice regarding food and medication.',
            'exercise_recommendations': 'Avoid strenuous physical activity until cleared by a doctor.',
            'hydration_advice': 'Follow your healthcare provider’s direct instructions.',
            'healthy_weight_tips': 'Visit the nearest hospital immediately.'
        }
    return {
        'lifestyle_suggestions': '',
        'diet_recommendations': '',
        'exercise_recommendations': '',
        'hydration_advice': '',
        'healthy_weight_tips': ''
    }

def get_color_for_stage(stage_name):
    if stage_name == 'Stage 1':
        return 'yellow'
    elif stage_name == 'Stage 2':
        return 'orange'
    elif stage_name == 'Hypertensive Crisis':
        return 'red'
    return 'blue'

def predict_hypertension(form_data):
    """
    Validates data, arranges into pandas DataFrame according to feature_order,
    predicts using the model, and formats the output.
    """
    global _ht_model, _ht_feature_order, _ht_stage_mapping
    
    if _ht_model is None or _ht_feature_order is None or _ht_stage_mapping is None:
        return {
            'status': 'error',
            'message': 'Hypertension model is not loaded. Please contact support.'
        }
        
    try:
        # Extract features according to feature order
        # 'age', 'sex', 'BMI', 'Resi', 'SBP', 'DBP', 'Smoking', 'odisease', 'creantine', 'BUN', 'Noofmed'
        
        # Intercept Height and Weight to calculate BMI if BMI is not explicitly provided
        if 'BMI' in _ht_feature_order:
            try:
                weight = float(form_data.get('Weight', 0))
                height = float(form_data.get('Height', 0))
                if height > 0:
                    form_data['BMI'] = weight / (height * height)
                else:
                    form_data['BMI'] = 0.0
            except ValueError:
                form_data['BMI'] = 0.0

        feature_dict = {}
        for feature in _ht_feature_order:
            # Get value from form, default to 0 if missing/invalid
            raw_val = form_data.get(feature, 0)
            try:
                feature_dict[feature] = float(raw_val)
            except ValueError:
                feature_dict[feature] = 0.0
                
        # Create a pandas DataFrame with one row
        input_df = pd.DataFrame([feature_dict])
        
        # Make prediction
        prediction_num = _ht_model.predict(input_df)[0]
        proba = _ht_model.predict_proba(input_df)[0]
        prob_pct = int(max(proba) * 100)
        
        # Map numeric label to string
        stage_name = _ht_stage_mapping.get(int(prediction_num), "Unknown")
        
        # Construct response
        result = {
            'status': 'success',
            'stage': stage_name,
            'riskLevel': stage_name, # Alias to match existing UI logic
            'probability': prob_pct,
            'color': get_color_for_stage(stage_name),
            'recommendations': get_recommendations(stage_name),
            'input_data': feature_dict  # Useful for debugging or displaying in UI
        }
        return result
        
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }
