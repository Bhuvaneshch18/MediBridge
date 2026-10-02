import joblib
import numpy as np

hd_model = joblib.load('knn_heart.pkl')

hd_features_2 = [45, 0, 1, 120, 200, 0, 0, 150, 0, 0.0, 2, 0, 1]
X_hd_2 = np.array([hd_features_2])
hd_proba_2 = hd_model.predict_proba(X_hd_2)[0]
hd_pos_idx = 1
print(f"Heart prob 2: {int(hd_proba_2[hd_pos_idx]*100)}%")

hd_features_3 = [55, 1, 0, 130, 230, 0, 1, 110, 1, 1.0, 1, 1, 3]
X_hd_3 = np.array([hd_features_3])
hd_proba_3 = hd_model.predict_proba(X_hd_3)[0]
print(f"Heart prob 3: {int(hd_proba_3[hd_pos_idx]*100)}%")

hd_features_4 = [60, 1, 1, 140, 250, 0, 1, 130, 0, 1.0, 1, 0, 2]
X_hd_4 = np.array([hd_features_4])
hd_proba_4 = hd_model.predict_proba(X_hd_4)[0]
print(f"Heart prob 4: {int(hd_proba_4[hd_pos_idx]*100)}%")

