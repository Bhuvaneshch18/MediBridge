import os
import joblib
import pandas as pd

# Global variables to store bundle contents
_asthma_model = None
_asthma_feature_order = None
_asthma_label_mapping = None
_asthma_encoders = None

def init_asthma_model(app_root_path):
    """
    Loads the asthma_model_bundle.pkl exactly once at startup.
    """
    global _asthma_model, _asthma_feature_order, _asthma_label_mapping, _asthma_encoders
    
    bundle_path = os.path.join(app_root_path, 'asthma_model_bundle.pkl')
    
    try:
        if os.path.exists(bundle_path):
            bundle = joblib.load(bundle_path)
            _asthma_model = bundle.get('model')
            _asthma_feature_order = bundle.get('feature_order')
            _asthma_label_mapping = bundle.get('label_mapping')
            _asthma_encoders = bundle.get('encoders')
            print("✓ Asthma Model Bundle Loaded Successfully")
        else:
            print("! Asthma model bundle not found. Predictions will fail gracefully.")
    except Exception as e:
        print(f"! Failed to load asthma model bundle: {e}")

def get_recommendations(stage_name):
    """
    Returns personalized recommendations based on the predicted stage.
    """
    if stage_name == 'No Asthma':
        return {
            'lifestyle_suggestions': 'Continue maintaining a healthy lifestyle and avoid smoking and second-hand smoke.',
            'diet_recommendations': 'Maintain a balanced diet rich in antioxidants to support lung health.',
            'exercise_recommendations': 'Exercise regularly to keep your cardiovascular system strong.',
            'hydration_advice': 'Drink plenty of water to keep your respiratory tract hydrated.',
            'healthy_weight_tips': 'Schedule regular health check-ups if symptoms develop.'
        }
    elif stage_name == 'Asthma':
        return {
            'lifestyle_suggestions': 'Consult a pulmonologist for evaluation and avoid known allergens and air pollution.',
            'diet_recommendations': 'Avoid foods that may trigger acid reflux, which can worsen asthma symptoms.',
            'exercise_recommendations': 'Engage in light physical activity but keep your prescribed inhaler nearby.',
            'hydration_advice': 'Ensure adequate hydration to help thin out mucus in the airways.',
            'healthy_weight_tips': 'Seek immediate medical attention if severe breathing difficulty occurs.'
        }
    return {
        'lifestyle_suggestions': '',
        'diet_recommendations': '',
        'exercise_recommendations': '',
        'hydration_advice': '',
        'healthy_weight_tips': ''
    }

def get_color_for_stage(stage_name):
    if stage_name == 'No Asthma':
        return 'green'
    elif stage_name == 'Asthma':
        return 'red'
    return 'blue'

def predict_asthma(form_data):
    """
    Validates data, handles encoding, arranges into pandas DataFrame,
    predicts using CatBoost, and formats the output.
    """
    global _asthma_model, _asthma_feature_order, _asthma_label_mapping, _asthma_encoders
    
    if _asthma_model is None or _asthma_feature_order is None or _asthma_label_mapping is None or _asthma_encoders is None:
        return {
            'status': 'error',
            'message': 'Asthma model is not loaded. Please contact support.'
        }
        
    try:
        # Implicit BMI calculation
        if 'BMI' in _asthma_feature_order:
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
        for feature in _asthma_feature_order:
            raw_val = form_data.get(feature)
            
            # Check if this feature needs encoding
            if feature in _asthma_encoders:
                # Use the encoder
                encoder = _asthma_encoders[feature]
                
                # Provide safe defaults if input is completely missing
                if raw_val is None:
                    raw_val = encoder.classes_[0]  # Safe fallback to first class
                    
                # Safe fallback if input string is weirdly formatted or doesn't match
                if raw_val not in encoder.classes_:
                    raw_val = encoder.classes_[0]
                    
                try:
                    feature_dict[feature] = float(encoder.transform([raw_val])[0])
                except Exception:
                    feature_dict[feature] = 0.0
            else:
                # Numeric features
                try:
                    feature_dict[feature] = float(raw_val if raw_val is not None else 0.0)
                except ValueError:
                    feature_dict[feature] = 0.0
                
        # Create a pandas DataFrame with one row
        input_df = pd.DataFrame([feature_dict])
        
        # Make prediction
        prediction_num = _asthma_model.predict(input_df)[0]
        proba = _asthma_model.predict_proba(input_df)[0]
        prob_pct = int(max(proba) * 100)
        if prob_pct > 95:
            prob_pct = 95
        elif prob_pct < 5:
            prob_pct = 5
        
        # Map numeric label to string
        stage_name = _asthma_label_mapping.get(int(prediction_num), "Unknown")
        
        # Construct response
        result = {
            'status': 'success',
            'stage': stage_name,
            'riskLevel': stage_name,
            'probability': prob_pct,
            'color': get_color_for_stage(stage_name),
            'recommendations': get_recommendations(stage_name),
            'input_data': form_data  # raw form data for display
        }
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'status': 'error',
            'message': str(e)
        }
