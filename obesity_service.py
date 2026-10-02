import os
import joblib
import numpy as np

obesity_bundle = None

def init_obesity_model(app_root_path):
    global obesity_bundle
    try:
        model_path = os.path.join(app_root_path, 'obesity_model_bundle.pkl')
        obesity_bundle = joblib.load(model_path)
        print("✓ Obesity Model Bundle Loaded Successfully")
    except Exception as e:
        print(f"✗ Failed to load Obesity Model Bundle: {e}")

def get_advice_for_prediction(prediction_label):
    advice_map = {
        'Insufficient_Weight': {
            'color': 'blue',
            'category': 'Insufficient Weight',
            'riskLevel': 'Moderate Risk',
            'health_explanation': 'Your BMI is below the healthy range. Being underweight can compromise your immune system and bone health.',
            'lifestyle_suggestions': 'Focus on building muscle mass and ensuring you are getting enough essential nutrients.',
            'diet_recommendations': 'Increase your intake of nutrient-dense foods like nuts, avocados, whole grains, and lean proteins.',
            'exercise_recommendations': 'Engage in strength training to build healthy muscle mass rather than excessive cardio.',
            'hydration_advice': 'Drink water regularly, but avoid filling up on fluids right before meals.',
            'healthy_weight_tips': 'Eat smaller, more frequent meals if you struggle with eating large portions at once.'
        },
        'Normal_Weight': {
            'color': 'green',
            'category': 'Normal Weight',
            'riskLevel': 'Low Risk',
            'health_explanation': 'You are currently in a healthy weight range. Maintaining this weight significantly reduces your risk of chronic diseases.',
            'lifestyle_suggestions': 'Keep up the good work! Consistency is key to long-term health.',
            'diet_recommendations': 'Continue eating a balanced diet rich in vegetables, lean proteins, and complex carbohydrates.',
            'exercise_recommendations': 'Maintain a routine of at least 150 minutes of moderate aerobic activity per week.',
            'hydration_advice': 'Aim for 8-10 glasses of water daily to support digestion and metabolism.',
            'healthy_weight_tips': 'Weigh yourself periodically to ensure you remain in your healthy range.'
        },
        'Overweight_Level_I': {
            'color': 'yellow',
            'category': 'Overweight (Level I)',
            'riskLevel': 'Medium Risk',
            'health_explanation': 'You are slightly above the recommended weight range, which may increase the risk of metabolic issues over time.',
            'lifestyle_suggestions': 'Small, sustainable changes to your daily routine can help reverse this trend.',
            'diet_recommendations': 'Reduce intake of sugary drinks and heavily processed snacks.',
            'exercise_recommendations': 'Try to incorporate 30 minutes of brisk walking or moderate exercise into your daily routine.',
            'hydration_advice': 'Drink a glass of water before meals to help control portion sizes.',
            'healthy_weight_tips': 'Focus on portion control and mindful eating.'
        },
        'Overweight_Level_II': {
            'color': 'yellow',
            'category': 'Overweight (Level II)',
            'riskLevel': 'Medium Risk',
            'health_explanation': 'You are carrying excess weight that puts you closer to the obesity threshold, increasing cardiovascular risks.',
            'lifestyle_suggestions': 'Consider tracking your daily activity and caloric intake to identify areas for improvement.',
            'diet_recommendations': 'Prioritize lean proteins, vegetables, and whole grains while strictly limiting empty calories.',
            'exercise_recommendations': 'Aim for 4-5 days of moderate to vigorous physical activity per week.',
            'hydration_advice': 'Replace all calorie-containing beverages with water or unsweetened tea.',
            'healthy_weight_tips': 'Cook more meals at home to better control ingredients and portion sizes.'
        },
        'Obesity_Type_I': {
            'color': 'orange',
            'category': 'Obesity Type I',
            'riskLevel': 'High Risk',
            'health_explanation': 'Your weight classifies as Obesity Type I. This significantly increases your risk for type 2 diabetes and hypertension.',
            'lifestyle_suggestions': 'Consulting a healthcare provider or a registered dietitian is highly recommended.',
            'diet_recommendations': 'Adopt a structured, calorie-controlled diet focusing on high-fiber, nutrient-dense foods.',
            'exercise_recommendations': 'Start with low-impact exercises like swimming or cycling to protect your joints while burning calories.',
            'hydration_advice': 'Ensure adequate hydration throughout the day, which can sometimes be confused with hunger.',
            'healthy_weight_tips': 'Set realistic, gradual weight loss goals (e.g., 1-2 pounds per week).'
        },
        'Obesity_Type_II': {
            'color': 'red',
            'category': 'Obesity Type II',
            'riskLevel': 'Severe Risk',
            'health_explanation': 'Obesity Type II carries a severe risk of serious health complications including heart disease and severe metabolic syndrome.',
            'lifestyle_suggestions': 'Professional medical intervention and a structured weight management program are strongly advised.',
            'diet_recommendations': 'Work with a professional to create a sustainable, calorie-deficit meal plan.',
            'exercise_recommendations': 'Engage in medically supervised exercise programs tailored to your current fitness level.',
            'hydration_advice': 'Consistent hydration is critical for metabolic function and energy levels.',
            'healthy_weight_tips': 'Focus on non-scale victories like improved energy, better sleep, and increased mobility.'
        },
        'Obesity_Type_III': {
            'color': 'darkred',
            'category': 'Obesity Type III (Severe)',
            'riskLevel': 'Critical Risk',
            'health_explanation': 'Obesity Type III is considered severe and poses immediate, critical risks to your overall health and longevity.',
            'lifestyle_suggestions': 'Seek immediate medical guidance. Bariatric surgery or medically supervised weight loss programs may be appropriate options.',
            'diet_recommendations': 'A strict, medically supervised dietary intervention is necessary.',
            'exercise_recommendations': 'Focus on very low-impact movements and physical therapy to improve mobility safely.',
            'hydration_advice': 'Maintain strict hydration protocols as advised by your healthcare provider.',
            'healthy_weight_tips': 'Build a strong support system of healthcare professionals, family, and friends.'
        }
    }
    return advice_map.get(prediction_label, advice_map['Normal_Weight'])


def predict_obesity(form_data):
    if not obesity_bundle:
        return {"status": "error", "message": "Obesity model is not initialized."}
        
    try:
        model = obesity_bundle['model']
        encoders = obesity_bundle['encoders']
        feature_order = obesity_bundle['feature_order']
        
        # Parse inputs
        gender = form_data.get('Gender', 'Male')
        age = float(form_data.get('Age', 25))
        height = float(form_data.get('Height', 1.70))
        weight = float(form_data.get('Weight', 70))
        family_history = form_data.get('family_history_with_overweight', 'no')
        favc = form_data.get('FAVC', 'no')
        fcvc = float(form_data.get('FCVC', 2))
        ncp = float(form_data.get('NCP', 3))
        caec = form_data.get('CAEC', 'Sometimes')
        smoke = form_data.get('SMOKE', 'no')
        ch2o = float(form_data.get('CH2O', 2))
        scc = form_data.get('SCC', 'no')
        faf = float(form_data.get('FAF', 1))
        tue = float(form_data.get('TUE', 1))
        calc = form_data.get('CALC', 'Sometimes')
        mtrans = form_data.get('MTRANS', 'Public_Transportation')
        
        # Calculate BMI automatically
        bmi = weight / (height * height) if height > 0 else 0
        
        # Build features dict for easy ordering and encoding
        raw_features = {
            'Gender': gender,
            'Age': age,
            'Height': height,
            'Weight': weight,
            'family_history_with_overweight': family_history,
            'FAVC': favc,
            'FCVC': fcvc,
            'NCP': ncp,
            'CAEC': caec,
            'SMOKE': smoke,
            'CH2O': ch2o,
            'SCC': scc,
            'FAF': faf,
            'TUE': tue,
            'CALC': calc,
            'MTRANS': mtrans,
            'BMI': bmi
        }
        
        # Encode categorical variables using the label encoders
        encoded_features = []
        for feature_name in feature_order:
            val = raw_features[feature_name]
            if feature_name in encoders:
                try:
                    val_encoded = encoders[feature_name].transform([val])[0]
                except ValueError:
                    # In case of case mismatch, try Title case or capitalize
                    try:
                        val_encoded = encoders[feature_name].transform([str(val).title()])[0]
                    except ValueError:
                        val_encoded = encoders[feature_name].transform([str(val).capitalize()])[0]
                encoded_features.append(float(val_encoded))
            else:
                encoded_features.append(float(val))
                
        # Predict
        X = np.array([encoded_features])
        prediction_idx = model.predict(X)[0]
        prediction_label = encoders['Target'].inverse_transform([prediction_idx])[0]
        
        proba = model.predict_proba(X)[0]
        prob_pct = int(max(proba) * 100)
        if prob_pct > 95:
            prob_pct = 95
        elif prob_pct < 5:
            prob_pct = 5
        
        advice = get_advice_for_prediction(prediction_label)
        
        # Compile result
        result = {
            "status": "success",
            "prediction": prediction_label,
            "probability": prob_pct,
            "bmi": round(bmi, 2)
        }
        result.update(advice)
        return result
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
