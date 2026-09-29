# MediBridge Features & Resources Overview

Here is a comprehensive list of all the features in the MediBridge application, specifically highlighting the codebase resources, external APIs, machine learning models, and data feeds that power each feature:

### 1. User Authentication & Profile Management
Handles secure user registration, session cookies, Google OAuth sign-in, and profile updates.
*   **Backend Logic:** `auth/routes.py`, `auth/services.py`, `auth/utils.py`
*   **Database Models:** `User` model (`models.py`)
*   **External APIs:** Google OAuth 2.0 API (for "Sign in with Google").
*   **Libraries:** `Flask-Login` (session management), `Flask-Bcrypt` (password hashing).
*   **Frontend Templates:** `templates/login.html`, `templates/registration.html`, `templates/edit_profile.html`, `templates/forgot_password.html`

### 2. Disease Risk Assessments
Machine Learning-powered risk assessments for 5 specific conditions. Collects user health metrics via questionnaires and returns predicted risk levels.
*   **Backend Logic:** `app.py` (prediction routes), `obesity_service.py`, `hypertension_service.py`, `asthma_service.py`
*   **Machine Learning Models (Scikit-Learn):** 
    *   Heart Disease: `knn_heart.pkl` (trained on `heart.csv`)
    *   Diabetes: `knn_diabetes.pkl` (trained on `diabetes.csv`)
    *   Asthma: `asthma_model_bundle.pkl`
    *   Hypertension: `hypertension_model_bundle.pkl`
    *   Obesity: `obesity_model_bundle.pkl` (trained on `ObesityDataSet_raw_and_data_sinthetic_1.csv`)
*   **Database Models:** `Assessment` model (`models.py`)
*   **Frontend Templates:** `templates/assessment.html`, `templates/assessment_result.html`, `templates/obesity_result.html`, `templates/hypertension_result.html`, `templates/asthma_result.html`

### 3. Smart Health Chatbot
An interactive AI assistant capable of answering general health, lifestyle, and dietary questions.
*   **Backend Logic:** `app.py` (`/chat` route)
*   **External APIs:** Google Gemini AI API (`google-genai` Python SDK). Configured with a 5-key fallback array in `app.py` (`GEMINI_API_KEY` through `GEMINI_API_KEY_5`) to prevent quota limits.
*   **Frontend Integration:** Embedded chatbot UI within `templates/base.html`.

### 4. Prescription Analyzer
Allows users to upload images (JPG/PNG) or PDFs of their medical prescriptions. The system extracts and structures the medication names, dosages, and schedules.
*   **Backend Logic:** `app.py` (`/prescription` and `/analyze_prescription` routes)
*   **External APIs:** Google Gemini AI API (using Multimodal Vision capabilities for OCR and structuring).
*   **Database Models:** `Prescription` model (`models.py`)
*   **Frontend Templates:** `templates/prescription.html`, `templates/prescription_results_partial.html`

### 5. Daily Wellness Tracker
A holistic daily questionnaire that calculates a wellness score based on sleep, diet, exercise, and stress.
*   **Backend Logic:** `app.py` (`/wellness` and `/wellness_api` routes). Contains deterministic backend scoring logic (does NOT use AI).
*   **Database Models:** `QuestionnaireResponse` model (`models.py`)
*   **Frontend Templates:** `templates/wellness.html`
*   **Libraries:** `Chart.js` (for rendering historical wellness data charts).

### 6. Hospital & Clinic Finder
An interactive map that detects the user's location (or accepts manual input) and searches for nearby healthcare facilities.
*   **Backend Logic:** `app.py` (`/hospitals` and `/api/hospitals` routes)
*   **External APIs:** 
    *   **Overpass API:** Used to query OpenStreetMap data for hospitals and clinics.
    *   **OpenStreetMap API:** Map tiles and geographic data provider.
*   **Frontend Libraries:** Leaflet.js (for rendering the interactive map UI in `templates/hospitals.html`).

### 7. Health Articles & Education
A centralized hub providing users with verified medical news and disease-specific encyclopedic information.
*   **Backend Logic:** `app.py` (`/articles` and `/article/<disease>` routes)
*   **External Data Sources:**
    *   **Google News RSS Feeds:** `https://news.google.com/rss/search?q={disease}+health` (Parsed via `xml.etree.ElementTree` in `fetch_health_news()` to populate the dynamic news feed).
    *   **Wikipedia / Verified Medical Sources:** The `/article/<disease>` route explicitly redirects users to Wikipedia (e.g., `https://en.wikipedia.org/wiki/...`) to ensure information accuracy instead of generating medical articles via AI.
*   **Frontend Templates:** `templates/articles.html`, `templates/article.html`

### 8. User Dashboard & History
The central hub for logged-in users to view their health summary, recent assessment history, saved prescriptions, and wellness trends.
*   **Backend Logic:** `app.py` (`/dashboard`, `/history` routes)
*   **Frontend Templates:** `templates/home.html` (Dashboard view), `templates/history.html`

### 9. Feedback & Rating System
A non-intrusive popup that asks users to rate their MediBridge experience out of 5 stars once per active session.
*   **Backend Logic:** `app.py` (`/api/submit_rating` route)
*   **Database Models:** Tracks `has_rated` (Boolean) and `rating_value` (Integer) directly in the `User` table (`models.py`).
*   **Frontend Integration:** Custom Javascript state and CSS logic within the base templates.

### 10. Database & Core Infrastructure
*   **Web Framework:** Flask (`app.py`, `config.py`)
*   **Database:** PostgreSQL (`extensions.py`)
*   **ORM / Migrations:** SQLAlchemy, Flask-Migrate (`migrations/` directory)
*   **Configuration:** `.env` file (stores DB connection string, Gemini API keys, Google OAuth secrets)
*   **Styling:** Custom Vanilla CSS (`static/css/styles.css`) integrated with responsive HTML5 templates.
