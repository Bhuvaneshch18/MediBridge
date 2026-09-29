import os
import sys
import json
import traceback
import joblib
import numpy as np
import re
import time
from datetime import datetime
from obesity_service import init_obesity_model, predict_obesity
from hypertension_service import init_hypertension_model, predict_hypertension
from asthma_service import init_asthma_model, predict_asthma

# Force UTF-8 encoding for standard output to support checkmarks
sys.stdout.reconfigure(encoding='utf-8')

from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_login import login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from google import genai
from google.genai import types

from config import Config
from extensions import db, migrate, login_manager, bcrypt
from sqlalchemy import text
from models import User, Assessment, QuestionnaireResponse, Prescription
from auth import auth_bp
from services import create_assessment_record
import logging

load_dotenv()
print("✓ Environment variables loaded")

if os.environ.get("GEMINI_API_KEY"):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
else:
    client = genai.Client()

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)
bcrypt.init_app(app)

login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

@login_manager.unauthorized_handler
def unauthorized():
    return render_template('unauthorized.html', next=request.path), 401

@app.after_request
def add_header(response):
    """
    Add headers to prevent browser caching.
    """
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


app.register_blueprint(auth_bp, url_prefix='/auth')

print("✓ SQLAlchemy initialized")
print("✓ Flask-Migrate initialized")
print("✓ Authentication module initialized")
print("✓ Database Models Loaded")


# Initialize Obesity Model
init_obesity_model(app.root_path)

# Initialize Hypertension Model
init_hypertension_model(app.root_path)

# Initialize Asthma Model
init_asthma_model(app.root_path)

generic_questions = [
    {
        'category': 'Personal Information',
        'question': 'What is your age?',
        'field_name': 'age',
        'input_type': 'number',
        'min': 1,
        'max': 120,
        'required': True
    },
    {
        'category': 'Personal Information',
        'question': 'Biological Sex',
        'field_name': 'sex',
        'input_type': 'radio',
        'options': [
            {'value': 'male', 'label': 'Male'},
            {'value': 'female', 'label': 'Female'},
            {'value': 'other', 'label': 'Other'}
        ],
        'required': True
    },
    {
        'category': 'Personal Information',
        'question': 'Height (cm)',
        'explanation': 'Your height measured in centimeters (cm). E.g., 5 feet 7 inches is approximately 170 cm.',
        'field_name': 'height',
        'input_type': 'number',
        'min': 50,
        'max': 300,
        'required': True
    },
    {
        'category': 'Personal Information',
        'question': 'Weight (kg)',
        'explanation': 'Your current body weight in kilograms (kg). E.g., 154 lbs is approximately 70 kg.',
        'field_name': 'weight',
        'input_type': 'number',
        'min': 20,
        'max': 500,
        'required': True
    },
    {
        'category': 'Medical History',
        'question': 'Do you have a family history of this condition?',
        'explanation': 'Presence of this condition among immediate blood relatives (parents, siblings, or grandparents).',
        'field_name': 'family_history',
        'input_type': 'radio',
        'options': [
            {'value': 'yes', 'label': 'Yes (Diagnosed in immediate family members)'},
            {'value': 'no', 'label': 'No (No known family history)'},
            {'value': 'not_sure', 'label': 'Not Sure (Unknown or unconfirmed family history)'}
        ],
        'required': True
    },
    {
        'category': 'Medical History',
        'question': 'How often do you exercise per week?',
        'explanation': 'Physical activity includes moderate to intense exercise like brisk walking, cycling, swimming, or sports.',
        'field_name': 'exercise',
        'input_type': 'select',
        'options': [
            {'value': '', 'label': 'Select an option'},
            {'value': '0', 'label': 'Rarely or Never (Less than 30 mins per week)'},
            {'value': '1_2', 'label': '1-2 times (Light weekly exercise)'},
            {'value': '3_4', 'label': '3-4 times (Moderate regular workout schedule)'},
            {'value': '5+', 'label': '5 or more times (Vigorous daily or frequent exercise)'}
        ],
        'required': True
    },
    {
        'category': 'Symptoms',
        'question': 'Rate your current stress level',
        'explanation': 'A self-reported score from 1 (completely calm/relaxed) to 10 (extremely high stress/anxiety).',
        'field_name': 'stress_level',
        'input_type': 'slider',
        'min': 1,
        'max': 10,
        'required': True
    },
    {
        'category': 'Additional Information',
        'question': 'Any additional symptoms we should know about?',
        'explanation': 'Optional notes on any unusual physical signs, discomfort, or relevant clinical history.',
        'field_name': 'additional_info',
        'input_type': 'text',
        'required': False
    }
]

heart_disease_questions = [
    {
        'category': 'Clinical Metrics',
        'question': 'What is your age?',
        'field_name': 'age',
        'input_type': 'number',
        'min': 1,
        'max': 120,
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'Biological Sex',
        'field_name': 'sex',
        'input_type': 'radio',
        'options': [
            {'value': '1', 'label': 'Male'},
            {'value': '0', 'label': 'Female'}
        ],
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'What type of chest pain do you experience?',
        'explanation': 'Angina is chest pain caused by reduced blood flow to the heart. Select the option that best describes how your chest pain feels.',
        'field_name': 'cp',
        'input_type': 'radio',
        'options': [
            {'value': '0', 'label': 'Typical Angina (Heavy squeezing pressure or tightness during physical exertion)'},
            {'value': '1', 'label': 'Atypical Angina (Sharp, fleeting, or brief chest discomfort not tied to exercise)'},
            {'value': '2', 'label': 'Non-Anginal Pain (Chest pain from non-heart causes like muscle strain or acid reflux)'},
            {'value': '3', 'label': 'Asymptomatic (No chest pain or pressure experienced)'}
        ],
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'Resting Blood Pressure (Top number, usually around 120 mmHg)',
        'explanation': 'Systolic blood pressure measured while resting. A normal reading for a healthy adult is typically under 120 mmHg.',
        'field_name': 'trestbps',
        'input_type': 'number',
        'min': 50,
        'max': 250,
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'Cholesterol level (mg/dL)',
        'explanation': 'Total cholesterol measured from a blood test (lipid panel). Normal level for adults is usually below 200 mg/dL.',
        'field_name': 'chol',
        'input_type': 'number',
        'min': 100,
        'max': 600,
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'Is your Fasting Blood Sugar higher than 120 mg/dL?',
        'explanation': 'Fasting Blood Sugar measures glucose after not eating for at least 8 hours. If you do not have a lab report and have no diabetes diagnosis, select "No".',
        'field_name': 'fbs',
        'input_type': 'radio',
        'options': [
            {'value': '1', 'label': 'Yes (> 120 mg/dL: High fasting blood sugar level)'},
            {'value': '0', 'label': 'No (<= 120 mg/dL: Normal fasting blood sugar level)'}
        ],
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'Does your ECG/EKG report show any abnormalities?',
        'explanation': 'An ECG (Electrocardiogram) is a medical test report that records the electrical signals of your heart to check for abnormal heart rhythms or muscle damage. If you have an ECG test report from a doctor, select its result. If you do not have an ECG report or do not know the result, select "Normal".',
        'field_name': 'restecg',
        'input_type': 'radio',
        'options': [
            {'value': '0', 'label': 'Normal (No abnormal heart rhythms or electrical defects on ECG report)'},
            {'value': '1', 'label': 'ST-T Wave Abnormality (Irregular heartbeat pattern or reduced blood/oxygen supply to heart)'},
            {'value': '2', 'label': 'Left Ventricular Hypertrophy (Thickened heart muscle wall, often due to high blood pressure)'}
        ],
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'Maximum Heart Rate achieved during exercise',
        'explanation': 'Peak heart rate (beats per minute) during intense exercise or a treadmill stress test. Estimated maximum heart rate is roughly 220 minus your age.',
        'field_name': 'thalach',
        'input_type': 'number',
        'min': 50,
        'max': 250,
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'Do you experience chest pain when you exercise?',
        'explanation': 'Exercise-induced angina happens when the heart muscle demands more oxygen during physical activity than blood vessels can supply.',
        'field_name': 'exang',
        'input_type': 'radio',
        'options': [
            {'value': '1', 'label': 'Yes (Chest pain or pressure is triggered by physical activity)'},
            {'value': '0', 'label': 'No (No chest pain during physical exercise)'}
        ],
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'Does your ECG report show ST-segment depression during exercise?',
        'explanation': 'ST-segment depression on an ECG stress test report measures stress on the heart under workload. Look for "ST Depression" or "Oldpeak" on your ECG report. If you do not have an ECG report, enter 0.',
        'field_name': 'oldpeak',
        'input_type': 'number',
        'min': 0,
        'max': 10,
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'Slope of the peak exercise ST segment',
        'explanation': 'Refers to the ST-slope graph on an ECG treadmill stress test. If you do not have an ECG stress test report, select "Flat".',
        'field_name': 'slope',
        'input_type': 'radio',
        'options': [
            {'value': '0', 'label': 'Upsloping (Normal healthy heart electrical recovery during exercise)'},
            {'value': '1', 'label': 'Flat (Mildly abnormal heart electrical recovery during physical stress)'},
            {'value': '2', 'label': 'Downsloping (Abnormal heart electrical recovery, indicates potential oxygen shortage)'}
        ],
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'Number of major vessels colored by fluoroscopy',
        'explanation': 'Number of major heart blood vessels (0 to 3) seen under fluoroscopy (cardiac angiogram imaging). If you have not had a cardiac angiogram scan, enter 0.',
        'field_name': 'ca',
        'input_type': 'number',
        'min': 0,
        'max': 3,
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'Do you have Thalassemia or cardiac blood flow defect?',
        'explanation': 'Thalassemia is an inherited blood disorder. On heart stress test reports, "defect" refers to blood circulation deficits in heart tissue. If unknown, select "Normal".',
        'field_name': 'thal',
        'input_type': 'radio',
        'options': [
            {'value': '1', 'label': 'Normal (Healthy blood flow and normal red blood cell structure)'},
            {'value': '2', 'label': 'Fixed Defect (Permanent blood flow deficit, often from prior heart muscle scarring)'},
            {'value': '3', 'label': 'Reversable Defect (Temporary blood flow deficit occurring only during exercise)'}
        ],
        'required': True
    }
]

diabetes_questions = [
    {
        'category': 'Clinical Metrics',
        'question': 'Number of times pregnant (Enter 0 if male or never pregnant)',
        'explanation': 'Total number of full-term or partial pregnancies. Enter 0 for biological males or if you have never been pregnant.',
        'field_name': 'Pregnancies',
        'input_type': 'number',
        'min': 0,
        'max': 20,
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'Glucose concentration (from your blood test report in mg/dL)',
        'explanation': 'Plasma glucose concentration measured after a fasting blood test or 2-hour oral glucose tolerance test. Healthy fasting level is under 100 mg/dL; prediabetes is 100-125 mg/dL; diabetes is 126+ mg/dL.',
        'field_name': 'Glucose',
        'input_type': 'number',
        'min': 0,
        'max': 300,
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'Diastolic Blood Pressure (The bottom number, e.g., the 80 in 120/80 mmHg)',
        'explanation': 'Diastolic blood pressure measures pressure in your arteries when your heart rests between beats. Normal resting level is typically 60-80 mmHg.',
        'field_name': 'BloodPressure',
        'input_type': 'number',
        'min': 0,
        'max': 200,
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'Triceps skin fold thickness (mm)',
        'explanation': 'A specialized skinfold caliper measurement taken at the back of the arm to estimate body fat. If you do not have a skinfold caliper lab result, keep the standard neutral average value of 20 mm.',
        'field_name': 'SkinThickness',
        'input_type': 'number',
        'min': 0,
        'max': 100,
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': '2-Hour Serum Insulin level (mu U/mL)',
        'explanation': 'A laboratory blood test measuring insulin hormone concentration 2 hours post-meal. If you do not have an insulin blood test report, keep the standard default baseline of 80 mu U/mL.',
        'field_name': 'Insulin',
        'input_type': 'number',
        'min': 0,
        'max': 1000,
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'Body Mass Index (BMI)',
        'explanation': 'Body Mass Index is calculated as Weight (kg) divided by Height (m)^2. Healthy weight is 18.5–24.9; Overweight is 25–29.9; Obesity is 30 or higher.',
        'field_name': 'BMI',
        'input_type': 'number',
        'min': 0,
        'max': 70,
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'Genetic risk score (Diabetes Pedigree Function)',
        'explanation': 'A clinical formula calculating genetic diabetes risk based on family history. If you do not have a calculated pedigree risk score from a geneticist, keep the baseline score of 0.5.',
        'field_name': 'DiabetesPedigreeFunction',
        'input_type': 'number',
        'min': 0,
        'max': 3,
        'required': True
    },
    {
        'category': 'Clinical Metrics',
        'question': 'What is your age?',
        'field_name': 'Age',
        'input_type': 'number',
        'min': 1,
        'max': 120,
        'required': True
    }
]

pneumonia_questions = [
    # Step 1 Personal Information
    {
        'category': 'Personal Information',
        'question': 'Age',
        'field_name': 'age',
        'input_type': 'number',
        'min': 1,
        'max': 120,
        'required': True
    },
    {
        'category': 'Personal Information',
        'question': 'Gender',
        'field_name': 'gender',
        'input_type': 'radio',
        'options': [
            {'value': 'male', 'label': 'Male'},
            {'value': 'female', 'label': 'Female'},
            {'value': 'other', 'label': 'Other'}
        ],
        'required': True
    },
    # Step 2 Lifestyle
    {
        'category': 'Lifestyle',
        'question': 'Do you smoke?',
        'explanation': 'Active tobacco or cigarette smoking damages pulmonary defense mechanisms and increases lung infection vulnerability.',
        'field_name': 'smoking',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Active smoker)'}, {'value': 'no', 'label': 'No (Non-smoker)'}],
        'required': True
    },
    {
        'category': 'Lifestyle',
        'question': 'Are you exposed to second-hand smoke?',
        'explanation': 'Inhaling tobacco smoke from people smoking nearby, which irritates the respiratory tract.',
        'field_name': 'second_hand_smoke',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Regularly exposed)'}, {'value': 'no', 'label': 'No (Not exposed)'}],
        'required': True
    },
    {
        'category': 'Lifestyle',
        'question': 'Do you consume alcohol frequently?',
        'explanation': 'Frequent alcohol consumption can suppress alveolar macrophage immunity in the lungs.',
        'field_name': 'alcohol',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Frequent or heavy drinking)'}, {'value': 'no', 'label': 'No (Occasional or no alcohol)'}],
        'required': True
    },
    {
        'category': 'Lifestyle',
        'question': 'Are you exposed to air pollution or dust regularly?',
        'explanation': 'Regular workplace or environmental inhalation of chemical fumes, silica dust, or industrial smog.',
        'field_name': 'pollution_exposure',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Regular environmental or workplace dust/smog exposure)'}, {'value': 'no', 'label': 'No (Low exposure)'}],
        'required': True
    },
    # Step 3 Medical History
    {
        'category': 'Medical History',
        'question': 'Have you had pneumonia before?',
        'explanation': 'Prior episodes of bacterial or viral lung infection.',
        'field_name': 'previous_pneumonia',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Diagnosed with pneumonia in the past)'}, {'value': 'no', 'label': 'No (No past pneumonia)'}],
        'required': True
    },
    {
        'category': 'Medical History',
        'question': 'Do you have COPD or another chronic lung disease?',
        'explanation': 'COPD (Chronic Obstructive Pulmonary Disease) includes emphysema and chronic bronchitis.',
        'field_name': 'copd_lung_disease',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Diagnosed with COPD, emphysema, or chronic bronchitis)'}, {'value': 'no', 'label': 'No (No chronic lung disease)'}],
        'required': True
    },
    {
        'category': 'Medical History',
        'question': 'Do you have diabetes?',
        'explanation': 'Elevated blood sugar levels can weaken white blood cell responses against pulmonary bacteria.',
        'field_name': 'diabetes',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Diagnosed with Type 1 or Type 2 Diabetes)'}, {'value': 'no', 'label': 'No (No diabetes)'}],
        'required': True
    },
    {
        'category': 'Medical History',
        'question': 'Do you have heart disease?',
        'explanation': 'Chronic cardiovascular conditions can lead to fluid accumulation or impaired circulation in the lungs.',
        'field_name': 'heart_disease',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Diagnosed cardiovascular condition)'}, {'value': 'no', 'label': 'No (No heart disease)'}],
        'required': True
    },
    {
        'category': 'Medical History',
        'question': 'Is your immune system weakened?',
        'explanation': 'Immune suppression caused by medications, steroids, chemotherapy, or medical conditions.',
        'field_name': 'weakened_immune',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Immunocompromised or taking immune-suppressing drugs)'}, {'value': 'no', 'label': 'No (Normal immune system)'}],
        'required': True
    },
    # Step 4 Family History
    {
        'category': 'Family History',
        'question': 'Family history of chronic lung disease?',
        'field_name': 'family_lung_disease',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Parents or siblings with chronic lung illness)'}, {'value': 'no', 'label': 'No (No family history)'}],
        'required': True
    },
    {
        'category': 'Family History',
        'question': 'Family history of respiratory infections?',
        'field_name': 'family_respiratory_infections',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Frequent severe lung infections in family)'}, {'value': 'no', 'label': 'No (No family history)'}],
        'required': True
    },
    # Step 5 Symptoms
    {
        'category': 'Symptoms',
        'question': 'Fever',
        'explanation': 'Body temperature elevated above 38.0°C (100.4°F).',
        'field_name': 'fever',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Elevated body temperature)'}, {'value': 'no', 'label': 'No (Normal body temperature)'}],
        'required': True
    },
    {
        'category': 'Symptoms',
        'question': 'Chills',
        'explanation': 'Involuntary shivering or cold sensations accompanying a high fever.',
        'field_name': 'chills',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Experiencing cold shivers or chills)'}, {'value': 'no', 'label': 'No (No chills)'}],
        'required': True
    },
    {
        'category': 'Symptoms',
        'question': 'Persistent cough',
        'explanation': 'A continuous cough lasting several days or weeks.',
        'field_name': 'persistent_cough',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Ongoing frequent coughing)'}, {'value': 'no', 'label': 'No (No persistent cough)'}],
        'required': True
    },
    {
        'category': 'Symptoms',
        'question': 'Cough with mucus',
        'explanation': 'Productive cough bringing up yellow, green, or rusty-colored phlegm.',
        'field_name': 'cough_with_mucus',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Productive cough with colored phlegm/mucus)'}, {'value': 'no', 'label': 'No (Dry cough or no cough)'}],
        'required': True
    },
    {
        'category': 'Symptoms',
        'question': 'Chest pain while breathing',
        'explanation': 'Pleuritic pain: sharp chest pain that intensifies when taking a deep breath or coughing.',
        'field_name': 'chest_pain',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Sharp chest pain when inhaling deeply or coughing)'}, {'value': 'no', 'label': 'No (No breathing-related chest pain)'}],
        'required': True
    },
    {
        'category': 'Symptoms',
        'question': 'Shortness of breath',
        'explanation': 'Dyspnea: difficulty breathing, feeling winded, or tight chest airflow.',
        'field_name': 'shortness_of_breath',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Struggling for breath or feeling winded)'}, {'value': 'no', 'label': 'No (Normal breathing effort)'}],
        'required': True
    },
    {
        'category': 'Symptoms',
        'question': 'Rapid breathing',
        'explanation': 'Tachypnea: unusually fast shallow breathing at rest (>20 breaths per minute).',
        'field_name': 'rapid_breathing',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Unusually fast or shallow breathing)'}, {'value': 'no', 'label': 'No (Normal breath rate)'}],
        'required': True
    },
    {
        'category': 'Symptoms',
        'question': 'Fatigue',
        'explanation': 'Severe weakness, exhaustion, or lack of energy.',
        'field_name': 'fatigue',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Feeling unusually exhausted or weak)'}, {'value': 'no', 'label': 'No (Normal energy level)'}],
        'required': True
    },
    {
        'category': 'Symptoms',
        'question': 'Sweating',
        'explanation': 'Excessive sweating or drenching night sweats associated with fever spikes.',
        'field_name': 'sweating',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Heavy sweating or night sweats)'}, {'value': 'no', 'label': 'No (Normal sweating)'}],
        'required': True
    },
    {
        'category': 'Symptoms',
        'question': 'Confusion (especially in elderly)',
        'explanation': 'Sudden disorientation, altered mental awareness, or acute cognitive changes.',
        'field_name': 'confusion',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Experiencing mental confusion or disorientation)'}, {'value': 'no', 'label': 'No (Clear mental state)'}],
        'required': True
    },
    # Step 6 Basic Health Measurements
    {
        'category': 'Basic Health Measurements',
        'question': 'Body Temperature (°C)',
        'explanation': 'Body temperature measured with a thermometer. Normal is 36.5°C–37.5°C. Fever is >= 38.0°C (100.4°F).',
        'field_name': 'body_temperature',
        'input_type': 'number',
        'min': 35,
        'max': 42,
        'required': True
    },
    {
        'category': 'Basic Health Measurements',
        'question': 'Oxygen Saturation (SpO₂) %',
        'explanation': 'SpO2 percentage measured using a pulse oximeter on your finger. Healthy range is 95%–100%. Below 92% requires prompt medical evaluation.',
        'field_name': 'oxygen_saturation',
        'input_type': 'number',
        'min': 50,
        'max': 100,
        'required': True
    },
    {
        'category': 'Basic Health Measurements',
        'question': 'Respiratory Rate (breaths/min)',
        'explanation': 'Number of breaths taken per minute while resting. Normal adult resting rate is 12–20 breaths per minute.',
        'field_name': 'respiratory_rate',
        'input_type': 'number',
        'min': 5,
        'max': 60,
        'required': True
    }
]

asthma_questions = [
    {
        'category': 'Personal Information',
        'question': 'What is your age? (Average adult age is around 45)',
        'field_name': 'Age',
        'input_type': 'number',
        'min': 1,
        'max': 120,
        'required': True
    },
    {
        'category': 'Personal Information',
        'question': 'What is your biological sex?',
        'field_name': 'Gender',
        'input_type': 'radio',
        'options': [{'value': 'Male', 'label': 'Male'}, {'value': 'Female', 'label': 'Female'}, {'value': 'Other', 'label': 'Other'}],
        'required': True
    },
    {
        'category': 'Personal Information',
        'question': 'What is your height in meters?',
        'explanation': 'If you only know your height in feet and inches, convert it (e.g., 5 feet 7 inches = 1.70 meters). If unknown, enter the average of 1.70.',
        'field_name': 'Height',
        'input_type': 'number',
        'min': 0.5,
        'max': 3.0,
        'required': True
    },
    {
        'category': 'Personal Information',
        'question': 'What is your weight in kg?',
        'explanation': 'If you only know your weight in pounds, divide by 2.2 to get kg (e.g., 154 lbs = 70 kg). If unknown, enter the average of 70.',
        'field_name': 'Weight',
        'input_type': 'number',
        'min': 10,
        'max': 500,
        'required': True
    },
    {
        'category': 'Lifestyle',
        'question': 'What is your current smoking status?',
        'explanation': 'Active or past tobacco smoke damages bronchial lining cilia, increasing airway hyper-reactivity.',
        'field_name': 'Smoking_Status',
        'input_type': 'radio',
        'options': [{'value': 'Never', 'label': 'Never (Never smoked or used tobacco)'}, {'value': 'Former', 'label': 'Former (Previously smoked but currently quit)'}, {'value': 'Current', 'label': 'Current (Active daily or regular smoker)'}],
        'required': True
    },
    {
        'category': 'Medical History',
        'question': 'Is there a family history of Asthma?',
        'explanation': 'Inherited genetic tendency to allergic inflammation or reactive airway disease from parents or siblings.',
        'field_name': 'Family_History',
        'input_type': 'radio',
        'options': [{'value': '1', 'label': 'Yes (Family history of asthma or allergic disease)'}, {'value': '0', 'label': 'No (No family history)'}],
        'required': True
    },
    {
        'category': 'Medical History',
        'question': 'What kind of allergies do you have?',
        'explanation': 'Allergens trigger IgE immune responses that inflame airway passages and precipitate asthma attacks.',
        'field_name': 'Allergies',
        'input_type': 'radio',
        'options': [
            {'value': 'None', 'label': 'None (No known environmental allergies)'},
            {'value': 'Dust', 'label': 'Dust (Allergic to dust mites or indoor dust)'},
            {'value': 'Pets', 'label': 'Pets (Allergic to animal dander, fur, or feathers)'},
            {'value': 'Pollen', 'label': 'Pollen (Seasonal allergic rhinitis / hay fever)'},
            {'value': 'Multiple', 'label': 'Multiple (Sensitive to multiple allergic triggers)'}
        ],
        'required': True
    },
    {
        'category': 'Lifestyle',
        'question': 'What is the air pollution level where you live?',
        'explanation': 'Inhalation of fine airborne dust (PM2.5) or vehicle emissions irritates sensitive bronchial tissues.',
        'field_name': 'Air_Pollution_Level',
        'input_type': 'radio',
        'options': [{'value': 'Low', 'label': 'Low (Clean suburban or rural air quality)'}, {'value': 'Moderate', 'label': 'Moderate (Urban city air quality)'}, {'value': 'High', 'label': 'High (Dense smog, industrial area, or high vehicle emissions)'}],
        'required': True
    },
    {
        'category': 'Lifestyle',
        'question': 'What is your physical activity level?',
        'explanation': 'Evaluates general cardiorespiratory fitness versus exercise-induced bronchospasm risk.',
        'field_name': 'Physical_Activity_Level',
        'input_type': 'radio',
        'options': [{'value': 'Active', 'label': 'Active (Regular workouts or active manual work)'}, {'value': 'Moderate', 'label': 'Moderate (Light walks or weekly exercise)'}, {'value': 'Sedentary', 'label': 'Sedentary (Mostly sitting, minimal exercise)'}],
        'required': True
    },
    {
        'category': 'Lifestyle',
        'question': 'What is your occupation type?',
        'explanation': 'Workplace environments determine exposure to indoor mold/dust vs outdoor pollen/industrial fumes.',
        'field_name': 'Occupation_Type',
        'input_type': 'radio',
        'options': [{'value': 'Indoor', 'label': 'Indoor (Office, home, or indoor facility work)'}, {'value': 'Outdoor', 'label': 'Outdoor (Field, construction, or outdoor work)'}],
        'required': True
    },
    {
        'category': 'Medical History',
        'question': 'Do you have any comorbidities? (Other chronic conditions)',
        'explanation': 'Co-existing long-term health conditions that can affect lung function and treatment.',
        'field_name': 'Comorbidities',
        'input_type': 'radio',
        'options': [
            {'value': 'None', 'label': 'None (No other chronic health conditions)'},
            {'value': 'Diabetes', 'label': 'Diabetes (Chronic high blood sugar condition)'},
            {'value': 'Hypertension', 'label': 'Hypertension (Chronic high blood pressure condition)'},
            {'value': 'Both', 'label': 'Both (Diagnosed with both diabetes and high blood pressure)'}
        ],
        'required': True
    },
    {
        'category': 'Medical Readings',
        'question': 'Medication Adherence (0 to 10)',
        'explanation': 'How strictly do you follow prescribed inhaler or medication schedules? 0 means never, 10 means always. If you take no medications, enter 5 as a neutral default.',
        'field_name': 'Medication_Adherence',
        'input_type': 'number',
        'min': 0,
        'max': 10,
        'required': True
    },
    {
        'category': 'Medical History',
        'question': 'Number of Emergency Room visits in the past year for breathing issues',
        'explanation': 'Frequency of severe acute asthma exacerbations requiring emergency treatment. Enter 0 if none.',
        'field_name': 'Number_of_ER_Visits',
        'input_type': 'number',
        'min': 0,
        'max': 50,
        'required': True
    },
    {
        'category': 'Medical Readings',
        'question': 'Peak Expiratory Flow (L/min)',
        'explanation': 'Peak Expiratory Flow (PEF) is a spirometry test measuring maximum speed of exhalation. Normal healthy adult range is 400-700 L/min. If untested, enter 500.',
        'field_name': 'Peak_Expiratory_Flow',
        'input_type': 'number',
        'min': 50,
        'max': 1000,
        'required': True
    },
    {
        'category': 'Medical Readings',
        'question': 'FeNO Level (ppb)',
        'explanation': 'Fractional Exhaled Nitric Oxide (FeNO) test measures allergic airway inflammation in parts per billion. Normal is < 25 ppb. If untested, enter 15.',
        'field_name': 'FeNO_Level',
        'input_type': 'number',
        'min': 0,
        'max': 200,
        'required': True
    }
]

hypertension_questions = [
    {
        'category': 'Personal Information',
        'question': 'What is your age? (Average adult age is around 45)',
        'field_name': 'age',
        'input_type': 'number',
        'min': 1,
        'max': 120,
        'required': True
    },
    {
        'category': 'Personal Information',
        'question': 'What is your biological sex?',
        'field_name': 'sex',
        'input_type': 'radio',
        'options': [{'value': '1', 'label': 'Male'}, {'value': '0', 'label': 'Female'}],
        'required': True
    },
    {
        'category': 'Personal Information',
        'question': 'What is your height in meters?',
        'explanation': 'If you only know your height in feet and inches, convert it (e.g., 5 feet 7 inches = 1.70 meters). If unknown, enter the average of 1.70.',
        'field_name': 'Height',
        'input_type': 'number',
        'min': 0.5,
        'max': 3.0,
        'required': True
    },
    {
        'category': 'Personal Information',
        'question': 'What is your weight in kg?',
        'explanation': 'If you only know your weight in pounds, divide by 2.2 to get kg (e.g., 154 lbs = 70 kg). If unknown, enter the average of 70.',
        'field_name': 'Weight',
        'input_type': 'number',
        'min': 10,
        'max': 500,
        'required': True
    },
    {
        'category': 'Lifestyle',
        'question': 'Where do you currently live?',
        'explanation': 'Urban living environments are statistically linked to higher dietary sodium intake, environmental noise, and stress.',
        'field_name': 'Resi',
        'input_type': 'radio',
        'options': [{'value': '1', 'label': 'Urban (City or dense suburban area)'}, {'value': '0', 'label': 'Rural (Countryside or rural village environment)'}],
        'required': True
    },
    {
        'category': 'Medical Readings',
        'question': 'What is your Systolic Blood Pressure?',
        'explanation': 'Systolic blood pressure is the "top number" (mmHg) measuring arterial pressure when your heart contracts. Normal is under 120 mmHg.',
        'field_name': 'SBP',
        'input_type': 'number',
        'min': 50,
        'max': 250,
        'required': True
    },
    {
        'category': 'Medical Readings',
        'question': 'What is your Diastolic Blood Pressure?',
        'explanation': 'Diastolic blood pressure is the "bottom number" (mmHg) measuring arterial pressure when your heart rests between beats. Normal is under 80 mmHg.',
        'field_name': 'DBP',
        'input_type': 'number',
        'min': 30,
        'max': 150,
        'required': True
    },
    {
        'category': 'Lifestyle',
        'question': 'Do you currently smoke or use tobacco products?',
        'explanation': 'Nicotine immediately causes temporary vessel constriction and damages blood vessel walls over time.',
        'field_name': 'Smoking',
        'input_type': 'radio',
        'options': [{'value': '1', 'label': 'Yes (Currently smoke or use tobacco)'}, {'value': '0', 'label': 'No (Non-smoker)'}],
        'required': True
    },
    {
        'category': 'Medical History',
        'question': 'Do you suffer from any other chronic diseases? (e.g., Diabetes, Heart Disease)',
        'explanation': 'Co-existing chronic conditions like diabetes or kidney disease accelerate vascular stiffness.',
        'field_name': 'odisease',
        'input_type': 'radio',
        'options': [{'value': '1', 'label': 'Yes (Diagnosed with other chronic health conditions)'}, {'value': '0', 'label': 'No (No other chronic health conditions)'}],
        'required': True
    },
    {
        'category': 'Lab Results',
        'question': 'What is your Creatinine level (mg/dL)?',
        'explanation': 'Serum Creatinine (mg/dL) is a blood test marker evaluating kidney filtering function. Normal range is 0.7–1.3 mg/dL. If untested, enter 1.0.',
        'field_name': 'creantine',
        'input_type': 'number',
        'min': 0.1,
        'max': 15.0,
        'required': True
    },
    {
        'category': 'Lab Results',
        'question': 'What is your Blood Urea Nitrogen (BUN) level (mg/dL)?',
        'explanation': 'Blood Urea Nitrogen (BUN) measures nitrogenous waste in your blood to evaluate kidney health. Normal is 7–20 mg/dL. If untested, enter 15.',
        'field_name': 'BUN',
        'input_type': 'number',
        'min': 1,
        'max': 100,
        'required': True
    },
    {
        'category': 'Medical History',
        'question': 'How many prescription medications do you take daily?',
        'explanation': 'Total count of daily prescription maintenance drugs. Enter 0 if none.',
        'field_name': 'Noofmed',
        'input_type': 'number',
        'min': 0,
        'max': 20,
        'required': True
    }
]

obesity_questions = [
    {
        'category': 'Personal Information',
        'question': 'Biological Sex',
        'field_name': 'Gender',
        'input_type': 'radio',
        'options': [{'value': 'Male', 'label': 'Male'}, {'value': 'Female', 'label': 'Female'}],
        'required': True
    },
    {
        'category': 'Personal Information',
        'question': 'What is your age?',
        'field_name': 'Age',
        'input_type': 'number',
        'min': 1,
        'max': 120,
        'required': True
    },
    {
        'category': 'Personal Information',
        'question': 'What is your height in meters? (e.g., 1.70)',
        'explanation': 'If you only know your height in feet and inches, convert it (e.g., 5 feet 7 inches = 1.70 meters). If unknown, enter the average of 1.70.',
        'field_name': 'Height',
        'input_type': 'number',
        'min': 0.5,
        'max': 3.0,
        'required': True
    },
    {
        'category': 'Personal Information',
        'question': 'What is your weight in kg?',
        'explanation': 'If you only know your weight in pounds, divide by 2.2 to get kg (e.g., 154 lbs = 70 kg). If unknown, enter the average of 70.',
        'field_name': 'Weight',
        'input_type': 'number',
        'min': 10,
        'max': 500,
        'required': True
    },
    {
        'category': 'Family History',
        'question': 'Does anyone in your immediate family suffer from being overweight?',
        'explanation': 'Family history evaluates genetic and shared dietary predispositions to weight gain.',
        'field_name': 'family_history_with_overweight',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Family history of overweight or obesity)'}, {'value': 'no', 'label': 'No (No family history)'}],
        'required': True
    },
    {
        'category': 'Dietary Habits',
        'question': 'Do you frequently eat high-calorie food or fast food?',
        'explanation': 'FAVC: Frequent consumption of high energy-density foods (fried items, processed fast food, soft drinks).',
        'field_name': 'FAVC',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Regularly eat high-calorie fast food or fried items)'}, {'value': 'no', 'label': 'No (Rarely or never eat junk food)'}],
        'required': True
    },
    {
        'category': 'Dietary Habits',
        'question': 'How often do you eat vegetables? (1 = Rarely, 2 = Sometimes, 3 = Always)',
        'explanation': 'FCVC: Frequency of vegetable consumption per main meal (1 = Rarely/never, 2 = Occasionally, 3 = Always with meals).',
        'field_name': 'FCVC',
        'input_type': 'slider',
        'min': 1,
        'max': 3,
        'required': True
    },
    {
        'category': 'Dietary Habits',
        'question': 'How many main meals do you eat daily?',
        'explanation': 'NCP: Number of primary main meals consumed per day.',
        'field_name': 'NCP',
        'input_type': 'select',
        'options': [{'value': '1', 'label': '1 meal (Single main meal per day)'}, {'value': '2', 'label': '2 meals (Two main meals per day)'}, {'value': '3', 'label': '3 meals (Standard 3 main meals per day)'}, {'value': '4', 'label': '4 or more meals (Frequent main meals per day)'}],
        'required': True
    },
    {
        'category': 'Dietary Habits',
        'question': 'Do you eat snacks between your main meals?',
        'explanation': 'CAEC: Consumption of food between main meals (snacking habits).',
        'field_name': 'CAEC',
        'input_type': 'select',
        'options': [{'value': 'no', 'label': 'No (Do not snack between main meals)'}, {'value': 'Sometimes', 'label': 'Sometimes (Occasional light snacking)'}, {'value': 'Frequently', 'label': 'Frequently (Regular daily snacking between meals)'}, {'value': 'Always', 'label': 'Always (Continuous snacking throughout the day)'}],
        'required': True
    },
    {
        'category': 'Lifestyle',
        'question': 'Do you smoke or use tobacco?',
        'explanation': 'Active smoking status affecting basal metabolic rate.',
        'field_name': 'SMOKE',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Active smoker)'}, {'value': 'no', 'label': 'No (Non-smoker)'}],
        'required': True
    },
    {
        'category': 'Dietary Habits',
        'question': 'How much water do you drink daily? (1 = Less than 1 liter, 2 = 1 to 2 liters, 3 = More than 2 liters)',
        'explanation': 'CH2O: Daily hydration intake (1 = Under 1L, 2 = 1–2L, 3 = Over 2L).',
        'field_name': 'CH2O',
        'input_type': 'slider',
        'min': 1,
        'max': 3,
        'required': True
    },
    {
        'category': 'Lifestyle',
        'question': 'Do you actively monitor your daily calorie intake?',
        'explanation': 'SCC: Self-monitoring of daily calorie consumption.',
        'field_name': 'SCC',
        'input_type': 'radio',
        'options': [{'value': 'yes', 'label': 'Yes (Actively log or track daily calories)'}, {'value': 'no', 'label': 'No (Do not track daily calories)'}],
        'required': True
    },
    {
        'category': 'Lifestyle',
        'question': 'How often do you exercise or do physical activity? (0 = Never, 1 = 1-2 days, 2 = 3-4 days, 3 = 5+ days)',
        'explanation': 'FAF: Frequency of physical activity per week (0 = None, 1 = 1-2 days, 2 = 3-4 days, 3 = 5+ days).',
        'field_name': 'FAF',
        'input_type': 'slider',
        'min': 0,
        'max': 3,
        'required': True
    },
    {
        'category': 'Lifestyle',
        'question': 'How much time do you spend using screens (TV, phone, computer) daily? (0 = 0-2 hours, 1 = 3-5 hours, 2 = 5+ hours)',
        'explanation': 'TUE: Time using technology/screens daily (0 = 0–2 hrs, 1 = 3–5 hrs, 2 = >5 hrs).',
        'field_name': 'TUE',
        'input_type': 'slider',
        'min': 0,
        'max': 2,
        'required': True
    },
    {
        'category': 'Dietary Habits',
        'question': 'How often do you consume alcohol?',
        'explanation': 'CALC: Alcohol intake frequency.',
        'field_name': 'CALC',
        'input_type': 'select',
        'options': [{'value': 'no', 'label': 'No (Do not drink alcohol)'}, {'value': 'Sometimes', 'label': 'Sometimes (Occasional social drinking)'}, {'value': 'Frequently', 'label': 'Frequently (Weekly or frequent alcohol consumption)'}, {'value': 'Always', 'label': 'Always (Daily or heavy alcohol consumption)'}],
        'required': True
    },
    {
        'category': 'Lifestyle',
        'question': 'What is your primary method of transportation?',
        'explanation': 'MTRANS: Daily transportation mode evaluating physical energy expenditure.',
        'field_name': 'MTRANS',
        'input_type': 'select',
        'options': [{'value': 'Walking', 'label': 'Walking (On foot)'}, {'value': 'Bike', 'label': 'Bicycle (Manual cycling)'}, {'value': 'Motorbike', 'label': 'Motorbike (Motorcycle or scooter)'}, {'value': 'Public_Transportation', 'label': 'Public Transportation (Bus, subway, or train)'}, {'value': 'Automobile', 'label': 'Automobile (Personal car or private vehicle)'}],
        'required': True
    }
]

@app.route('/')
def home():
    # We now rely on current_user directly in the template
    return render_template('home.html')

@app.route('/diseases', methods=['GET', 'POST'])
def diseases():
    return render_template('diagnose.html')

@app.route('/assessment/<disease_id>', methods=['GET', 'POST'])
@login_required
def assessment(disease_id):
    disease_titles = {
        'heart': 'Heart Disease',
        'diabetes': 'Diabetes',
        'pneumonia': 'Pneumonia',
        'hypertension': 'Hypertension',
        'obesity': 'Obesity',
        'asthma': 'Asthma'
    }
    title = disease_titles.get(disease_id, 'Health Condition')
    
    if disease_id == 'heart':
        questions_list = heart_disease_questions
    elif disease_id == 'diabetes':
        questions_list = diabetes_questions
    elif disease_id == 'pneumonia':
        questions_list = pneumonia_questions
    elif disease_id == 'hypertension':
        questions_list = hypertension_questions
    elif disease_id == 'asthma':
        questions_list = asthma_questions
    elif disease_id == 'obesity':
        questions_list = obesity_questions
    else:
        questions_list = generic_questions
    
    if request.method == 'POST':
        form_data = dict(request.form)
        
        try:
            if disease_id in ['heart', 'diabetes']:
                
                if disease_id == 'heart':
                    model_path = os.path.join(app.root_path, 'knn_heart.pkl')
                    model_loaded = joblib.load(model_path)
                    
                    def safe_float(val, default=0.0):
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            return float(default)
                            
                    features = [
                        safe_float(form_data.get('age', 0)),
                        safe_float(form_data.get('sex', 0)),
                        safe_float(form_data.get('cp', 0)),
                        safe_float(form_data.get('trestbps', 0)),
                        safe_float(form_data.get('chol', 0)),
                        safe_float(form_data.get('fbs', 0)),
                        safe_float(form_data.get('restecg', 0)),
                        safe_float(form_data.get('thalach', 0)),
                        safe_float(form_data.get('exang', 0)),
                        safe_float(form_data.get('oldpeak', 0)),
                        safe_float(form_data.get('slope', 0)),
                        safe_float(form_data.get('ca', 0)),
                        safe_float(form_data.get('thal', 0))
                    ]
                elif disease_id == 'diabetes':
                    model_path = os.path.join(app.root_path, 'knn_diabetes.pkl')
                    model_loaded = joblib.load(model_path)
                    features = [
                        safe_float(form_data.get('Pregnancies', 0)),
                        safe_float(form_data.get('Glucose', 0)),
                        safe_float(form_data.get('BloodPressure', 0)),
                        safe_float(form_data.get('SkinThickness', 0)),
                        safe_float(form_data.get('Insulin', 0)),
                        safe_float(form_data.get('BMI', 0)),
                        safe_float(form_data.get('DiabetesPedigreeFunction', 0)),
                        safe_float(form_data.get('Age', 0))
                    ]
                
                X = np.array([features])
                prediction = model_loaded.predict(X)[0]
                proba = model_loaded.predict_proba(X)[0]
                classes = getattr(model_loaded, 'classes_', [0, 1])
                pos_idx = np.where(classes == 1)[0][0] if 1 in classes else 1
                pos_prob = proba[pos_idx]
                prob_pct = int(pos_prob * 100)
                model_name_str = "KNN (K-Nearest Neighbors)"
                if prob_pct >= 70:
                    riskLevel = "High"
                    analysis = f"Based on our {model_name_str} model analysis, there are significant indicators and a high estimated risk ({prob_pct}%) for {title}. Please consult a healthcare professional immediately for a formal clinical evaluation."
                    recs = [
                        "Schedule an urgent appointment with a doctor or specialist.",
                        "Monitor your symptoms closely and do not delay medical attention.",
                        "Follow a medically prescribed diet and lifestyle plan tailored to your condition."
                    ]
                elif prob_pct >= 40:
                    riskLevel = "Medium"
                    analysis = f"Based on our {model_name_str} model analysis, you show medium risk indicators ({prob_pct}%) for {title}. Early lifestyle interventions and a routine medical check-up are recommended."
                    recs = [
                        "Schedule a check-up with a healthcare provider for preventive monitoring.",
                        "Adopt a balanced diet low in processed foods, sodium, and refined sugars.",
                        "Engage in at least 30 minutes of daily moderate physical activity."
                    ]
                else:
                    riskLevel = "Low"
                    analysis = f"Based on our {model_name_str} model analysis, your indicators for {title} are currently low ({prob_pct}%). However, routine screening and healthy habits remain important for long-term prevention."
                    recs = [
                        "Maintain a healthy, nutrient-rich diet.",
                        "Continue routine annual health check-ups.",
                        "Stay physically active and monitor your vitals regularly."
                    ]
                
                if disease_id in ['heart', 'diabetes']:
                    print(f"[{title}] Prediction: {prediction}")
                    print(f"[{title}] Raw Probabilities: {proba}")
                    print(f"[{title}] Model Classes: {classes}")
                    print(f"[{title}] Positive Probability: {prob_pct}%")
                    print(f"[{title}] Risk Level: {riskLevel}")
                
                data = {
                    "riskLevel": riskLevel,
                    "probability": prob_pct,
                    "analysis": analysis,
                    "recommendations": recs,
                    "model_name": f"K-Nearest Neighbors (KNN) Classifier Model (knn_{disease_id}.pkl)"
                }
                
                session['assessment_result'] = data
                session['assessment_title'] = title
                
            elif disease_id == 'obesity':
                result = predict_obesity(form_data)
                if result.get('status') == 'success':
                    result['model_name'] = "Obesity Classification Model (obesity_model.pkl)"
                    session['assessment_result'] = result
                    session['assessment_title'] = title
                    
                    print(f"[{title}] Prediction Stage: {result.get('prediction')}")
                    print(f"[{title}] Stage Confidence Probability: {result.get('probability', 0)}%")
                    print(f"[{title}] Assigned Risk Level: {result.get('riskLevel', 'Unknown')}")
                    
                    # Log the assessment to the database
                    create_assessment_record(
                        user_id=current_user.id,
                        disease_name=title,
                        risk_level=result.get('riskLevel', 'Unknown'),
                        probability=result.get('probability', 0)
                    )
                    return redirect(url_for('obesity_result'))
                else:
                    flash(f"Error predicting obesity risk: {result.get('message')}", 'danger')
                    return redirect(url_for('diseases'))
                    
            elif disease_id == 'hypertension':
                result = predict_hypertension(form_data)
                if result.get('status') == 'success':
                    result['model_name'] = "Decision Tree Classifier Model (hypertension_model.pkl)"
                    session['assessment_result'] = result
                    session['assessment_title'] = title
                    
                    print(f"[{title}] Prediction Stage: {result.get('stage')}")
                    print(f"[{title}] Stage Confidence Probability: {result.get('probability', 0)}%")
                    print(f"[{title}] Assigned Risk Level: {result.get('riskLevel', 'Unknown')}")
                    
                    # Log the assessment to the database
                    create_assessment_record(
                        user_id=current_user.id,
                        disease_name=title,
                        risk_level=result.get('riskLevel', 'Unknown'),
                        probability=result.get('probability', 0)
                    )
                    return redirect(url_for('hypertension_result'))
                else:
                    flash(f"Error predicting hypertension risk: {result.get('message')}", 'danger')
                    return redirect(url_for('diseases'))
                    
            elif disease_id == 'asthma':
                result = predict_asthma(form_data)
                if result.get('status') == 'success':
                    result['model_name'] = "Random Forest Classifier Model (asthma_model.pkl)"
                    session['assessment_result'] = result
                    session['assessment_title'] = title
                    
                    print(f"[{title}] Prediction Stage: {result.get('stage')}")
                    print(f"[{title}] Stage Confidence Probability: {result.get('probability', 0)}%")
                    print(f"[{title}] Assigned Risk Level: {result.get('riskLevel', 'Unknown')}")
                    
                    # Log the assessment to the database
                    create_assessment_record(
                        user_id=current_user.id,
                        disease_name=title,
                        risk_level=result.get('riskLevel', 'Unknown'),
                        probability=result.get('probability', 0)
                    )
                    return redirect(url_for('asthma_result'))
                else:
                    flash(f"Error predicting asthma risk: {result.get('message')}", 'danger')
                    return redirect(url_for('diseases'))
                    
            else:
                flash("No ML model is currently available for this disease assessment.", "danger")
                return redirect(url_for('diseases'))
        except Exception as e:
            print(f"Error predicting disease risk: {e}")
            flash("An error occurred during risk assessment.", "danger")
            return redirect(url_for('diseases'))
            
        result_data = session.get('assessment_result', {})
        create_assessment_record(
            user_id=current_user.id,
            disease_name=title,
            risk_level=result_data.get('riskLevel', 'Unknown'),
            probability=result_data.get('probability', 0)
        )
            
        return redirect(url_for('assessment_result'))
        
    return render_template('assessment.html', title=title, questions=questions_list, disease_id=disease_id)

@app.route('/obesity_result')
@login_required
def obesity_result():
    result = session.get('assessment_result')
    title = session.get('assessment_title', 'Obesity Risk Assessment')
    
    if not result or result.get('status') != 'success':
        flash('No recent obesity assessment found.', 'warning')
        return redirect(url_for('diseases'))
        
    return render_template('obesity_result.html', result=result, title=title)

@app.route('/hypertension_result')
@login_required
def hypertension_result():
    result = session.get('assessment_result')
    title = session.get('assessment_title', 'Hypertension Risk Assessment')
    
    if not result or result.get('status') != 'success':
        flash('No recent hypertension assessment found.', 'warning')
        return redirect(url_for('diseases'))
        
    return render_template('hypertension_result.html', result=result, title=title)

@app.route('/asthma_result')
@login_required
def asthma_result():
    result = session.get('assessment_result')
    title = session.get('assessment_title', 'Asthma Risk Assessment')
    
    if not result or result.get('status') != 'success':
        flash('No recent asthma assessment found.', 'warning')
        return redirect(url_for('diseases'))
        
    return render_template('asthma_result.html', result=result, title=title)

@app.route('/assessment_result')
@login_required
def assessment_result():
    data = session.get('assessment_result')
    title = session.get('assessment_title', 'Health Condition')
    if not data:
        return redirect(url_for('diseases'))
    return render_template('assessment_result.html', data=data, title=title)



@app.route('/settings', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = current_user

    if request.method == 'POST':
        user.name = request.form['name']
        user.email = request.form['email']
        user.gender = request.form['gender']
        user.phone = request.form['phone']
        user.blood_group = request.form['blood_group']
        user.age = request.form['age']
        user.date_of_birth = request.form['date_of_birth']
        db.session.commit()
        return redirect(url_for('home'))

    return render_template('edit_profile.html', user=user)

@app.route('/dashboard')
@login_required
def dashboard():
    return redirect(url_for('auth.profile'))

@app.route('/profile')
@login_required
def profile_redirect():
    return redirect(url_for('auth.profile'))

@app.route('/history')
@login_required
def history():
    user_id = current_user.id
    assessments = Assessment.query.filter_by(user_id=user_id).order_by(Assessment.assessment_date.desc()).all()
    return render_template('history.html', assessments=assessments)

@app.route('/support')
@login_required
def support():
    return render_template('contact.html')




@app.route('/debug_models')
def debug_models():
    try:
        models = []
        for m in client.models.list_models():
            models.append(m.name)
        return jsonify(models)
    except Exception as e:
        return str(e)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
    
    try:
        system_prompt = "You are HealthPredict Assistant, a medical AI. Provide helpful, short information on diets, disease prevention, and cures. Format with basic HTML if needed. Keep answers concise."
        
        # Collect all API keys dynamically
        available_keys = []
        for key_name in ['GEMINI_API_KEY', 'GEMINI_API_KEY_1', 'GEMINI_API_KEY_2', 'GEMINI_API_KEY_3', 'GEMINI_API_KEY_4', 'GEMINI_API_KEY_5']:
            k = os.getenv(key_name)
            if k and k not in available_keys:
                available_keys.append(k)
                
        if not available_keys:
            available_keys = [os.getenv('GEMINI_API_KEY')]
            
        max_retries = len(available_keys) + 2
        current_key_idx = 0
        current_client = client if available_keys[0] == os.getenv('GEMINI_API_KEY') else genai.Client(api_key=available_keys[0])
        
        for attempt in range(max_retries):
            try:
                response = current_client.models.generate_content(model='gemini-3.1-flash-lite', contents=f"{system_prompt}\n\nUser: {user_message}")
                return jsonify({'response': response.text})
            except Exception as inner_e:
                error_msg = str(inner_e).lower()
                is_rate_limit = "429" in error_msg or "resourceexhausted" in error_msg or "quota" in error_msg
                is_unavailable = "503" in error_msg or "unavailable" in error_msg
                
                if is_rate_limit:
                    if current_key_idx < len(available_keys) - 1:
                        # Switch to the next available key instantly upon quota exhaustion
                        current_key_idx += 1
                        current_client = genai.Client(api_key=available_keys[current_key_idx])
                        continue # Retry immediately with next key
                    
                    # If all keys are exhausted, use backoff before giving up
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(2)
                        continue
                
                elif is_unavailable:
                    # Transient failures (e.g. 503) use existing exponential backoff
                    if attempt < max_retries - 1:
                        import time
                        time.sleep((attempt + 1) * 5)
                        continue
                        
                raise inner_e
                
    except Exception as e:
        print(f"Chat error: {e}")
        error_msg = str(e).lower()
        if "429" in error_msg or "resourceexhausted" in error_msg or "quota" in error_msg:
            return jsonify({'error': 'The AI assistant is temporarily unavailable due to rate limits. Please try again later.'}), 429
        elif "503" in error_msg or "unavailable" in error_msg:
            return jsonify({'error': 'The AI brain is experiencing high demand right now. Please try again in a moment.'}), 503
        elif "401" in error_msg or "403" in error_msg or "authentication" in error_msg:
            return jsonify({'error': 'Authentication error with the AI service. Please check configuration.'}), 401
        else:
            return jsonify({'error': 'I am having trouble connecting to the AI brain right now. Please try again later.'}), 500





@app.route('/wellness_api', methods=['POST'])
@login_required
def wellness_api():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    try:
        sleep = float(data.get('sleep', 0))
        hydration = float(data.get('hydration', 0))
        activity = float(data.get('activity', 0))
        screen_time = float(data.get('screen_time', 0))
    except ValueError:
        return jsonify({"error": "Invalid numerical input."}), 400
        
    pre_sleep_screens = data.get('pre_sleep_screens', "I don't avoid screens")
    meals = data.get('meals', '3')
    nutrition = data.get('nutrition', 'No')
    smoking = data.get('smoking', 'Daily')
    alcohol = data.get('alcohol', 'Daily')
    stress = data.get('stress', 'High')
    
    score = 0
    categories = []
    
    # 1. Sleep (10 points)
    if sleep >= 7:
        score += 10
        categories.append({"name": "Sleep", "score": "10 / 10", "status": "Good", "suggestion": "Keep maintaining a consistent sleep schedule."})
    elif sleep >= 5:
        score += 5
        categories.append({"name": "Sleep", "score": "5 / 10", "status": "Needs Improvement", "suggestion": "Try to get at least 7-8 hours of sleep per night for optimal recovery."})
    else:
        categories.append({"name": "Sleep", "score": "0 / 10", "status": "Needs Improvement", "suggestion": "Prioritize sleep. A consistent routine can help increase your resting hours."})
        
    # 2. Screen Time Before Sleep (10 points)
    if pre_sleep_screens in ["More than 1 hour", "30–60 minutes"]:
        score += 10
        categories.append({"name": "Pre-sleep Screens", "score": "10 / 10", "status": "Good", "suggestion": "Excellent sleep hygiene."})
    elif pre_sleep_screens == "15–30 minutes":
        score += 5
        categories.append({"name": "Pre-sleep Screens", "score": "5 / 10", "status": "Needs Improvement", "suggestion": "Try avoiding screens for at least 30 minutes before bed."})
    else:
        categories.append({"name": "Pre-sleep Screens", "score": "0 / 10", "status": "Needs Improvement", "suggestion": "Blue light disrupts sleep. Try reading a book before bed instead."})

    # 3. Hydration (10 points)
    if hydration >= 2.0:
        score += 10
        categories.append({"name": "Hydration", "score": "10 / 10", "status": "Good", "suggestion": "Great job staying hydrated."})
    elif hydration >= 1.0:
        score += 5
        categories.append({"name": "Hydration", "score": "5 / 10", "status": "Needs Improvement", "suggestion": "Try to carry a water bottle to increase your daily water intake."})
    else:
        categories.append({"name": "Hydration", "score": "0 / 10", "status": "Needs Improvement", "suggestion": "Your hydration is very low. Aim for at least 2 liters of water daily."})
        
    # 4. Meals (10 points)
    if meals in ["3", "4"]:
        score += 10
        categories.append({"name": "Meals", "score": "10 / 10", "status": "Good", "suggestion": "You have a balanced eating schedule."})
    elif meals in ["2", "5 or more"]:
        score += 5
        categories.append({"name": "Meals", "score": "5 / 10", "status": "Needs Improvement", "suggestion": "Try to stick to 3 balanced meals to regulate your metabolism."})
    else:
        categories.append({"name": "Meals", "score": "0 / 10", "status": "Needs Improvement", "suggestion": "Eating only one meal can disrupt energy levels. Try eating smaller, more frequent meals."})

    # 5. Nutrition (10 points)
    if nutrition == 'Yes':
        score += 10
        categories.append({"name": "Nutrition", "score": "10 / 10", "status": "Good", "suggestion": "Good job including fruits or vegetables today."})
    else:
        categories.append({"name": "Nutrition", "score": "0 / 10", "status": "Needs Improvement", "suggestion": "Try to add a piece of fruit or a serving of vegetables to your meals."})
        
    # 6. Physical Activity (10 points)
    if activity >= 30:
        score += 10
        categories.append({"name": "Physical Activity", "score": "10 / 10", "status": "Good", "suggestion": "Excellent daily movement."})
    elif activity >= 15:
        score += 5
        categories.append({"name": "Physical Activity", "score": "5 / 10", "status": "Needs Improvement", "suggestion": "Try to gradually increase your daily movement to at least 30 minutes."})
    else:
        categories.append({"name": "Physical Activity", "score": "0 / 10", "status": "Needs Improvement", "suggestion": "Incorporate short walks or light stretching into your day."})
        
    # 7. Screen Time (10 points)
    if screen_time <= 2:
        score += 10
        categories.append({"name": "Screen Time", "score": "10 / 10", "status": "Good", "suggestion": "Great screen time management."})
    elif screen_time <= 5:
        score += 5
        categories.append({"name": "Screen Time", "score": "5 / 10", "status": "Needs Improvement", "suggestion": "Try taking regular breaks away from screens."})
    else:
        categories.append({"name": "Screen Time", "score": "0 / 10", "status": "Needs Improvement", "suggestion": "Consider setting limits on recreational screen time before bed."})

    # 8. Smoking (10 points)
    if smoking == "Never":
        score += 10
        categories.append({"name": "Smoking", "score": "10 / 10", "status": "Good", "suggestion": "Excellent job avoiding smoking."})
    elif smoking == "Occasionally":
        score += 5
        categories.append({"name": "Smoking", "score": "5 / 10", "status": "Needs Improvement", "suggestion": "Consider reducing or quitting to protect your lungs and heart."})
    else:
        categories.append({"name": "Smoking", "score": "0 / 10", "status": "Needs Improvement", "suggestion": "Frequent smoking is harmful to your health. Please consider seeking resources to quit."})

    # 9. Alcohol (10 points)
    if alcohol in ["Never", "Occasionally"]:
        score += 10
        categories.append({"name": "Alcohol", "score": "10 / 10", "status": "Good", "suggestion": "Great job managing alcohol consumption."})
    elif alcohol == "1–2 times a week":
        score += 5
        categories.append({"name": "Alcohol", "score": "5 / 10", "status": "Needs Improvement", "suggestion": "Try to ensure you have several alcohol-free days per week."})
    else:
        categories.append({"name": "Alcohol", "score": "0 / 10", "status": "Needs Improvement", "suggestion": "Frequent alcohol consumption can impact liver and sleep health. Consider cutting back."})

    # 10. Stress (10 points)
    if stress == 'Low':
        score += 10
        categories.append({"name": "Stress", "score": "10 / 10", "status": "Good", "suggestion": "Your stress management is going well."})
    elif stress == 'Moderate':
        score += 5
        categories.append({"name": "Stress", "score": "5 / 10", "status": "Needs Improvement", "suggestion": "Consider taking short relaxation breaks to lower stress."})
    else:
        categories.append({"name": "Stress", "score": "0 / 10", "status": "Needs Improvement", "suggestion": "High stress can affect health. Try deep breathing, meditation, or speaking to someone."})

    # Overall Status
    if score >= 90:
        overall_status = "Excellent"
    elif score >= 75:
        overall_status = "Good"
    elif score >= 50:
        overall_status = "Fair"
    else:
        overall_status = "Needs Improvement"
        
    strengths = [cat['name'] for cat in categories if cat['status'] == 'Good']
    improvements = [cat for cat in categories if cat['status'] == 'Needs Improvement']
    
    summary = f"Your overall wellness score is {overall_status.lower()}. Focus on your areas for improvement to boost your score tomorrow!"
    if strengths:
        summary = f"Great job on {', '.join(strengths[:2])}! " + summary
        
    from models import WellnessScore
    from extensions import db
    new_wellness = WellnessScore(
        user_id=current_user.id,
        score=score,
        status=overall_status,
        summary=summary
    )
    db.session.add(new_wellness)
    db.session.commit()
    
    return jsonify({
        "score": score,
        "status": overall_status,
        "categories": categories,
        "strengths": strengths,
        "improvements": improvements,
        "summary": summary
    })

@app.route('/wellness')
@login_required
def wellness():
    return render_template('wellness.html')

import time
import requests
import xml.etree.ElementTree as ET

ARTICLE_CACHE = {
    'timestamp': 0,
    'articles': []
}

def fetch_health_news():
    global ARTICLE_CACHE
    current_time = time.time()
    # Refresh cache every 6 hours (21600 seconds)
    if current_time - ARTICLE_CACHE['timestamp'] < 21600 and ARTICLE_CACHE['articles']:
        return ARTICLE_CACHE['articles']
    
    try:
        diseases = ["Diabetes", "Heart Disease", "Hypertension", "Asthma", "Obesity"]
        articles = []
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        import random
        color_map = {
            "Diabetes": "0EA5E9",
            "Heart Disease": "EF4444",
            "Hypertension": "F59E0B",
            "Asthma": "10B981",
            "Obesity": "8B5CF6"
        }
        
        for disease in diseases:
            url = f"https://news.google.com/rss/search?q={disease}+health&hl=en-US&gl=US&ceid=US:en"
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code != 200:
                continue
                
            root = ET.fromstring(response.content)
            count = 0
            
            for item in root.findall('.//item'):
                title = item.findtext('title')
                link = item.findtext('link')
                pubDate = item.findtext('pubDate')
                
                if not title or not link:
                    continue
                    
                formatted_date = pubDate[:16] if pubDate else 'Recent'
                color = color_map.get(disease, "0EA5E9")
                
                articles.append({
                    'title': title,
                    'link': link,
                    'description': f"Recent updates and medical news regarding {disease}. Click to read the full coverage.",
                    'date': formatted_date,
                    'category': disease,
                    'image': f'https://placehold.co/600x400/{color}/FFFFFF?text={disease.replace(" ", "+")}'
                })
                
                count += 1
                if count >= 3:  # 3 articles per disease = 15 articles total
                    break
                    
        if articles:
            random.shuffle(articles)
            ARTICLE_CACHE['articles'] = articles
            ARTICLE_CACHE['timestamp'] = current_time
            return articles
            
    except Exception as e:
        print(f"Error fetching external articles: {e}")
        
    return ARTICLE_CACHE['articles']

@app.route('/articles')
def articles():
    health_articles = fetch_health_news()
    return render_template('articles.html', articles=health_articles)

@app.route('/diet')
def diet():
    return render_template('diet.html')

@app.route('/prescription')
@login_required
def prescription():
    return render_template('prescription.html')

@app.route('/analyze_prescription', methods=['POST'])
@login_required
def analyze_prescription():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    allowed_extensions = {'png', 'jpg', 'jpeg', 'pdf'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed_extensions:
        return jsonify({'error': f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"}), 400
    
    try:
        image_bytes = file.read()
        
        # 4 MB limit (4 * 1024 * 1024 bytes)
        if len(image_bytes) > 4 * 1024 * 1024:
            return jsonify({'error': 'File is too large. Maximum size is 4 MB.'}), 400
            
        mime_type = file.mimetype
        

        prompt = """
        You are a medical AI assistant. Analyze this prescription image. 
        Extract the medicines, their dosages, timings, and any general notes.
        Return ONLY a raw JSON object with this exact structure (no markdown wrapper, no backticks):
        {
          "summary": {
            "medicines_count": 3,
            "days": 14,
            "morning": 2,
            "night": 1,
            "notes": ["Finish complete course", "Take after food"],
            "ai_explanation": "You have been prescribed medicines..."
          },
          "medicines": [
            {
              "name": "Medicine Name",
              "generic": "Generic Name",
              "type": "Tablet",
              "dosage": "1 Tablet",
              "timing": ["After Food", "Morning", "Night"],
              "duration": "14 Days",
              "purpose": "Controls blood pressure",
              "treats": ["Hypertension"],
              "how_it_works": "Relaxes blood vessels",
              "side_effects": "Dizziness",
              "precautions": "Avoid alcohol",
              "missed_dose": "Take as soon as you remember",
              "storage": "Room temperature"
            }
          ],
          "schedule": {
            "morning": ["Medicine Name 1 (After Food)"],
            "afternoon": [],
            "night": ["Medicine Name 1 (After Food)"]
          }
        }
        Do not wrap the JSON in ```json blocks. Just return the raw JSON string. If you cannot read the prescription clearly, make a best guess based on the visible text or return a simulated response if it's a test image.
        """
        
        image_parts = [
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        ]
        
        # Collect all API keys dynamically
        available_keys = []
        for key_name in ['GEMINI_API_KEY', 'GEMINI_API_KEY_2', 'GEMINI_API_KEY_3', 'GEMINI_API_KEY_4', 'GEMINI_API_KEY_5']:
            k = os.getenv(key_name)
            if k and k not in available_keys:
                available_keys.append(k)
                
        if not available_keys:
            available_keys = [os.getenv('GEMINI_API_KEY')]
            
        max_retries = len(available_keys) + 2
        current_key_idx = 0
        current_client = client if available_keys[0] == os.getenv('GEMINI_API_KEY') else genai.Client(api_key=available_keys[0])
        
        for attempt in range(max_retries):
            try:
                response = current_client.models.generate_content(
                    model='gemini-3.1-flash-lite',
                    contents=[prompt, image_parts[0]]
                )
                json_text = response.text
                
                match = re.search(r'\{.*\}', json_text, re.DOTALL)
                if match:
                    json_text = match.group(0)
                else:
                    raise ValueError("No JSON object found in response.")
                    
                data = json.loads(json_text)
                
                # Save the prescription analysis to the database so it appears in history
                from models import Prescription
                from extensions import db
                new_prescription = Prescription(
                    user_id=current_user.id,
                    file_name=file.filename,
                    file_path="Not saved locally (Serverless Mode)",
                    ai_summary=json_text
                )
                db.session.add(new_prescription)
                db.session.commit()
                
                return render_template('prescription_results_partial.html', data=data)
                
            except Exception as inner_e:
                error_msg = str(inner_e).lower()
                is_rate_limit = "429" in error_msg or "resourceexhausted" in error_msg or "quota" in error_msg
                is_unavailable = "503" in error_msg or "unavailable" in error_msg
                
                if is_rate_limit:
                    if current_key_idx < len(available_keys) - 1:
                        current_key_idx += 1
                        current_client = genai.Client(api_key=available_keys[current_key_idx])
                        continue
                        
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(2)
                        continue
                elif is_unavailable:
                    if attempt < max_retries - 1:
                        import time
                        time.sleep((attempt + 1) * 5)
                        continue
                        
                raise inner_e
        
    except Exception as e:
        print(f"Error in analyze_prescription:")
        traceback.print_exc()
        error_msg = str(e).lower()
        if "429" in error_msg or "resourceexhausted" in error_msg or "quota" in error_msg or "503" in error_msg:
            return jsonify({'error': "Prescription analysis is temporarily unavailable because the AI service has reached its usage limit. Please try again later."}), 503
        return jsonify({'error': f"Failed to process prescription: {str(e)}"}), 500


import time
hospital_cache = {}

@app.route('/api/toggle_hospital', methods=['POST'])
@login_required
def toggle_hospital():
    data = request.json
    if not data or not data.get('hospital_name'):
        return jsonify({'error': 'Missing hospital data'}), 400
        
    from models import SavedHospital
    from extensions import db
    
    hospital_name = data.get('hospital_name')
    address = data.get('address')
    lat = data.get('lat')
    lon = data.get('lon')
    
    existing = SavedHospital.query.filter_by(user_id=current_user.id, hospital_name=hospital_name).first()
    
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'status': 'unsaved'})
    else:
        new_hospital = SavedHospital(
            user_id=current_user.id,
            hospital_name=hospital_name,
            address=address,
            lat=float(lat) if lat else None,
            lon=float(lon) if lon else None
        )
        db.session.add(new_hospital)
        db.session.commit()
        return jsonify({'status': 'saved'})

@app.route('/api/hospitals')
def api_hospitals():
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    radius = request.args.get('radius', '25')
    
    if not lat or not lon:
        return jsonify({'error': 'Missing coordinates'}), 400
        
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except ValueError:
        return jsonify({'error': 'Invalid coordinates'}), 400
        
    # Server-side caching based on approx 1.1km grid to reduce Overpass load
    cache_key = f"{round(lat_f, 2)}_{round(lon_f, 2)}_{radius}"
    current_time = time.time()
    
    if cache_key in hospital_cache:
        cached_data, timestamp = hospital_cache[cache_key]
        if current_time - timestamp < 3600:  # 1 hour cache
            return jsonify({'elements': cached_data})
            
    radius_meters = float(radius) * 1000
    query = f"""[out:json][timeout:15];
(
  nwr["amenity"="hospital"](around:{radius_meters},{lat_f},{lon_f});
  nwr["amenity"="clinic"](around:{radius_meters},{lat_f},{lon_f});
  nwr["healthcare"="hospital"](around:{radius_meters},{lat_f},{lon_f});
  nwr["healthcare"="clinic"](around:{radius_meters},{lat_f},{lon_f});
  nwr["amenity"="doctors"](around:{radius_meters},{lat_f},{lon_f});
);
out center;"""

    # Multiple endpoints for fallback resilience
    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://z.overpass-api.de/api/interpreter"
    ]
    
    for endpoint in endpoints:
        try:
            resp = requests.get(endpoint, params={'data': query}, headers={'User-Agent': 'MediBridge/1.0 (contact@medibridge.local)'}, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                elements = data.get('elements', [])
                hospital_cache[cache_key] = (elements, current_time)
                return jsonify({'elements': elements})
            elif resp.status_code != 429 and resp.status_code != 504:
                # If it's a structural error, don't fallback to same Overpass mirrors
                print(f"Overpass Error {resp.status_code} on {endpoint}")
        except Exception as e:
            print(f"Overpass API timeout/error on {endpoint}: {e}")
            continue
            
    return jsonify({'error': 'Hospital search is temporarily unavailable.'}), 504

@app.route('/hospitals')
def hospitals():
    predicted_disease = request.args.get('disease', '')
    user_allow_location = False
    user_preferred_location = ''
    saved_hospital_names = []
    
    if current_user.is_authenticated:
        user_allow_location = getattr(current_user, 'allow_location', False)
        user_preferred_location = getattr(current_user, 'preferred_location', '') or ''
        
        from models import SavedHospital
        saved_hospitals = SavedHospital.query.filter_by(user_id=current_user.id).all()
        saved_hospital_names = [h.hospital_name for h in saved_hospitals]
        
    return render_template('hospitals.html', 
                           predicted_disease=predicted_disease,
                           user_allow_location=user_allow_location,
                           user_preferred_location=user_preferred_location,
                           saved_hospital_names=saved_hospital_names)

@app.route('/article/<disease>')
def article(disease):
    # Redirect to WebMD or Wikipedia as Gemini article generation is disabled
    search_query = disease.replace('_', ' ').replace('-', ' ')
    import urllib.parse
    return redirect(f"https://en.wikipedia.org/wiki/{urllib.parse.quote(search_query.title())}")

@app.route('/api/submit_rating', methods=['POST'])
@login_required
def submit_rating():
    data = request.get_json()
    if not data or 'rating' not in data:
        return jsonify({'error': 'No rating provided'}), 400
    
    current_user.has_rated = True
    current_user.rating_value = int(data['rating'])
    db.session.commit()
    
    return jsonify({'success': True}), 200

@app.after_request
def add_header(response):
    """
    Forces the browser to NEVER cache pages.
    This ensures that when a user logs out or leaves, they cannot use the back button
    or reopen a cached tab to bypass the login screen.
    """
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/debug_env')
def debug_env():
    import os
    client_id = os.environ.get('GOOGLE_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
    return {
        "has_client_id": bool(client_id),
        "client_id_starts_with": client_id[:5] if client_id else None,
        "has_client_secret": bool(client_secret),
        "config_client_id": bool(app.config.get('GOOGLE_CLIENT_ID'))
    }

with app.app_context():
    try:
        db.create_all()
        print("Database tables verified/created.")
    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == '__main__':
    import os
    is_dev = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(debug=is_dev)
