import streamlit as st
import google.generativeai as genai
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO
import os
import logging
import requests
import folium
from streamlit_folium import folium_static
from geopy.distance import geodesic
from deep_translator import GoogleTranslator
import pyttsx3
import speech_recognition as sr

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set up Gemini API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')  # Use environment variable
if not GOOGLE_API_KEY:
    st.error("Google API Key is missing! Set GOOGLE_API_KEY.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

translator = GoogleTranslator(source='auto', target='en')


def query_healthcare_assistant(symptoms, target_language='en'):
    if not symptoms.strip():
        return "Please provide valid symptoms."

    try:
        if target_language != 'en':
            symptoms = translator.translate(symptoms)

        prompt = f"""Analyze the following symptoms: {symptoms}.
        Provide possible conditions, advice, and diet recommendations.
        Format:
        Conditions:
        - Condition 1
        - Condition 2

        Advice:
        1. Step 1
        2. Step 2

        Diet & Lifestyle:
        - Recommendation 1
        - Recommendation 2
        """

        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return response.text if response else "Could not generate response."
    except Exception as e:
        logging.error(f"Error: {e}")
        return "Error generating response."


def create_pdf(report):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica", 12)
    c.drawString(100, 750, "Healthcare Report")
    c.drawString(100, 730, report)
    c.save()
    buffer.seek(0)
    return buffer


def get_coordinates(address):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json&limit=1"
        headers = {"User-Agent": "HealthcareAssistant/1.0"}
        response = requests.get(url, headers=headers)
        data = response.json()
        return (float(data[0]['lat']), float(data[0]['lon'])) if data else (None, None)
    except Exception as e:
        logging.error(f"Error fetching coordinates: {e}")
        return None, None


def text_to_speech(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()


def speech_to_text():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Speak now...")
        audio = r.listen(source)
    try:
        return r.recognize_google(audio)
    except sr.UnknownValueError:
        return "Speech not recognized."
    except sr.RequestError:
        return "Speech recognition service unavailable."


# Streamlit UI
st.set_page_config(page_title="Healthcare Assistant", layout="wide")
st.title("Clinical Prescription Chatbot")

language_options = {'English': 'en', 'Spanish': 'es', 'French': 'fr'}
language = st.sidebar.selectbox("Select Language", list(language_options.keys()))
target_language = language_options[language]

use_voice_input = st.sidebar.checkbox("Use Voice Input for Symptoms")
if use_voice_input and st.button("Click to Speak"):
    symptoms = speech_to_text()
    st.write(f"You said: {symptoms}")
else:
    symptoms = st.text_area("Describe your symptoms", "")

address = st.text_input("Enter your location:")
search_radius = st.slider("Search radius (km)", 1, 20, 5) * 1000

if st.button("Analyze Symptoms and Find Nearby Facilities"):
    if symptoms and address:
        with st.spinner("Processing..."):
            report = query_healthcare_assistant(symptoms, target_language)
            lat, lon = get_coordinates(address)

            if lat and lon:
                st.subheader("Symptom Analysis")
                st.write(report)
                st.download_button("Download Report", create_pdf(report), "healthcare_report.pdf")

                # Show Map
                st.subheader("Nearby Healthcare Facilities")
                m = folium.Map(location=[lat, lon], zoom_start=13)
                folium.Marker([lat, lon], popup="Your Location", icon=folium.Icon(color='red')).add_to(m)
                folium_static(m)
            else:
                st.error("Invalid address. Please enter a valid location.")
    else:
        st.warning("Please enter both symptoms and location.")
