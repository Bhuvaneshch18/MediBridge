import joblib
bundle = joblib.load('asthma_model_bundle.pkl')
print("Feature order:", bundle['feature_order'])
