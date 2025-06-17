import streamlit as st
import google.generativeai as genai
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from io import BytesIO
import os
import logging
import requests
import folium
from streamlit_folium import folium_static
from geopy.distance import geodesic
import streamlit.components.v1 as components
from deep_translator import GoogleTranslator
import pyttsx3
from gtts import gTTS

# Set page config
st.set_page_config(page_title="Healthcare Assistant", layout="wide")

# Set up logging
logging.basicConfig(level=logging.INFO)

# Set up Gemini AI API
os.environ['GOOGLE_API_KEY'] = ''
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])

# Initialize translator and TTS engine
tts_engine = pyttsx3.init()

# Language options
indian_languages = {
    "Hindi": "hi", "English": "en", "Telugu": "te", "Tamil": "ta",
    "Marathi": "mr", "Gujarati": "gu", "Kannada": "kn", "Malayalam": "ml",
    "Odia": "or", "Bengali": "bn", "Assamese": "as", "Punjabi": "pa", "Urdu": "ur"
}


# Function to translate and speak text
def translate_and_speak_text(text, language_code):
    try:
        translated_text = GoogleTranslator(source='auto', target=language_code).translate(text)
        tts = gTTS(text=translated_text, lang=language_code)
        tts.save("response.mp3")
        st.audio("response.mp3", format="audio/mp3")
        os.remove("response.mp3")  # Cleanup
        return translated_text
    except Exception as e:
        logging.error(f"Translation error: {e}")
        return text


# Function to query Gemini AI for symptom analysis
def query_healthcare_assistant(symptoms):
    prompt = f"Given the following symptoms: {symptoms}, list possible conditions and advice."
    model = genai.GenerativeModel('gemini-pro')
    try:
        response = model.generate_content(prompt)
        if response and response.parts:
            return response.text
        else:
            logging.error("No response parts found.")
            return "Sorry, there was an error generating the response."
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return "Sorry, there was an error generating the response."


# Function to create a healthcare report PDF
def create_pdf(report):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 50

    pdfmetrics.registerFont(TTFont('NotoSans', 'NotoSans-Regular.ttf'))
    c.setFont("NotoSans", 20)
    c.drawString(margin, height - margin, "Healthcare Report")
    c.setFont("NotoSans", 12)
    c.drawString(margin, height - margin - 30, report)
    c.save()
    buffer.seek(0)
    return buffer


# Function to get coordinates from an address
def get_coordinates(address):
    url = f"https://nominatim.openstreetmap.org/search?q={address}&format=json&limit=1"
    headers = {"User-Agent": "HealthcareAssistant/1.0"}
    response = requests.get(url, headers=headers)
    data = response.json()
    return (float(data[0]['lat']), float(data[0]['lon'])) if data else (None, None)


# Function to find nearby hospitals and pharmacies
def find_nearby_places(lat, lon, place_type, radius=5000):
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    (
      node["amenity"="{place_type}"](around:{radius},{lat},{lon});
      way["amenity"="{place_type}"](around:{radius},{lat},{lon});
    );
    out center;
    """
    try:
        response = requests.get(overpass_url, params={'data': overpass_query})
        data = response.json()
        return [{'lat': el['lat'], 'lon': el['lon']} for el in data.get('elements', []) if 'lat' in el and 'lon' in el]
    except Exception as e:
        logging.error(f"Nearby search error: {e}")
        return []


# Streamlit UI
st.title("Community Healthcare Chatbot Using AI")

symptoms = st.text_area("Describe your symptoms:")
address = st.text_input("Enter your location:")
search_radius = st.slider("Search radius for nearby facilities (km)", 1, 20, 5) * 1000
target_language = st.selectbox("Choose language for translation", list(indian_languages.keys()))

if st.button("Analyze Symptoms and Find Nearby Facilities"):
    if symptoms and address:
        report = query_healthcare_assistant(symptoms)
        language_code = indian_languages[target_language]
        translated_report = translate_and_speak_text(report, language_code)

        st.subheader("Symptom Analysis")
        st.write(translated_report)

        pdf = create_pdf(report)
        st.download_button(
            label="Download Report as PDF",
            data=pdf,
            file_name="healthcare_report.pdf",
            mime="application/pdf"
        )

        lat, lon = get_coordinates(address)
        if lat and lon:
            hospitals = find_nearby_places(lat, lon, "hospital", search_radius)
            pharmacies = find_nearby_places(lat, lon, "pharmacy", search_radius)

            st.subheader("Nearby Healthcare Facilities")
            m = folium.Map(location=[lat, lon], zoom_start=13)
            folium.Marker([lat, lon], popup="Your Location", icon=folium.Icon(color='red')).add_to(m)

            for place in hospitals:
                folium.Marker([place['lat'], place['lon']], popup="Hospital", icon=folium.Icon(color='blue')).add_to(m)
            for place in pharmacies:
                folium.Marker([place['lat'], place['lon']], popup="Pharmacy", icon=folium.Icon(color='green')).add_to(m)

            folium_static(m)
        else:
            st.error("Could not retrieve coordinates for the specified address.")
    else:
        st.warning("Please enter both symptoms and location.")
