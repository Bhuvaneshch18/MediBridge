import joblib
import numpy as np

dia_model = joblib.load('knn_diabetes.pkl')
dia_classes = getattr(dia_model, 'classes_', [0, 1])
dia_pos_idx = np.where(dia_classes == 1)[0][0] if 1 in dia_classes else 1

# Base slightly elevated features
for glucose in range(130, 170, 5):
    for bmi in range(28, 35, 1):
        for age in range(40, 60, 5):
            features = [2, glucose, 80, 25, 120, float(bmi), 0.5, age]
            X = np.array([features])
            proba = dia_model.predict_proba(X)[0]
            prob_pct = int(proba[dia_pos_idx] * 100)
            if 80 <= prob_pct <= 89:
                print(f"Found! Prob: {prob_pct}% -> {features}")
                import sys
                sys.exit(0)
