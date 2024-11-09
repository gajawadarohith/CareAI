import streamlit as st
import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai
import nltk
import re
from geopy.geocoders import Nominatim
import webbrowser
from PIL import Image
import io
import requests
from datetime import datetime

# Download required NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('averaged_perceptron_tagger')
nltk.download('maxent_ne_chunker')
nltk.download('words')

# Load environment variables
load_dotenv()

# Tokens and IDs
GEMINI_API_TOKEN = os.getenv("GEMINI_API_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# Configure logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=GEMINI_API_TOKEN)
model = genai.GenerativeModel('gemini-pro')

def send_emergency_alert_to_admin(emergency_details, uploaded_files):
    """Send emergency details and images to admin chat"""
    try:
        # Telegram API endpoint
        base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
        
        # Prepare emergency alert message
        alert_message = (
            "🚨 NEW EMERGENCY ALERT 🚨\n\n"
            f"Type: {emergency_details['type']}\n"
            f"Time: {emergency_details['time']}\n\n"
        )

        if emergency_details.get('location'):
            alert_message += f"📍 Location: {emergency_details['location']}\n"
            if emergency_details.get('coordinates'):
                alert_message += f"Coordinates: {emergency_details['coordinates']}\n"
        
        if emergency_details.get('address'):
            alert_message += f"🏠 Address: {emergency_details['address']}\n"

        # Send text message
        message_url = f"{base_url}/sendMessage"
        message_data = {
            "chat_id": ADMIN_CHAT_ID,
            "text": alert_message,
            "parse_mode": "HTML"
        }
        message_response = requests.post(message_url, json=message_data)

        # Send location if coordinates are available
        if emergency_details.get('coordinates'):
            lat, lon = emergency_details['coordinates']
            location_url = f"{base_url}/sendLocation"
            location_data = {
                "chat_id": ADMIN_CHAT_ID,
                "latitude": lat,
                "longitude": lon
            }
            location_response = requests.post(location_url, json=location_data)

        # Send photos if any
        if uploaded_files:
            photo_url = f"{base_url}/sendPhoto"
            for file in uploaded_files:
                files = {
                    "photo": file.getvalue()
                }
                photo_data = {
                    "chat_id": ADMIN_CHAT_ID,
                    "caption": "Emergency situation photo"
                }
                photo_response = requests.post(photo_url, data=photo_data, files=files)

        return True
    except Exception as e:
        logger.error(f"Failed to send emergency alert: {e}")
        return False

# Initialize session state
if 'step' not in st.session_state:
    st.session_state.step = 'emergency_type'
if 'emergency_type' not in st.session_state:
    st.session_state.emergency_type = None
if 'location_choice' not in st.session_state:
    st.session_state.location_choice = None
if 'location' not in st.session_state:
    st.session_state.location = None
if 'address' not in st.session_state:
    st.session_state.address = None
if 'photos' not in st.session_state:
    st.session_state.photos = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'alert_sent' not in st.session_state:
    st.session_state.alert_sent = False

def main():
    st.set_page_config(page_title="Emergency Assistance Bot", page_icon="🚑")
    
    # Title and description
    st.title("🚑 Emergency Assistance Bot")
    
    # Platform choice
    platform = st.radio(
        "Choose how you'd like to continue:",
        ("Continue in Streamlit", "Continue in Telegram")
    )
    
    if platform == "Continue in Telegram":
        st.markdown("Click the button below to open Telegram:")
        if st.button("Open Telegram Bot"):
            webbrowser.open("https://t.me/EmergencyEagleBot")
        st.stop()

    # Progress based on steps
    if st.session_state.step == 'emergency_type':
        st.markdown("### Please select the type of emergency:")
        emergency_options = ["Medical Emergency", "Accident", "Heart/Chest Pain", "Pregnancy"]
        selected_emergency = st.selectbox("Emergency Type", emergency_options)
        
        if st.button("Confirm Emergency Type"):
            st.session_state.emergency_type = selected_emergency
            st.session_state.step = 'location_choice'
            st.rerun()

    elif st.session_state.step == 'location_choice':
        st.markdown(f"### Selected Emergency: {st.session_state.emergency_type}")
        st.markdown("### Would you like to share your location?")
        location_choice = st.radio("Location sharing", ("Yes", "No"))
        
        if st.button("Confirm Location Choice"):
            st.session_state.location_choice = location_choice
            st.session_state.step = 'location_input'
            st.rerun()

    elif st.session_state.step == 'location_input':
        if st.session_state.location_choice == "Yes":
            st.markdown("### Please enter your coordinates:")
            col1, col2 = st.columns(2)
            with col1:
                latitude = st.number_input("Latitude", -90.0, 90.0, 0.0)
            with col2:
                longitude = st.number_input("Longitude", -180.0, 180.0, 0.0)
            
            if st.button("Submit Location"):
                st.session_state.location = (latitude, longitude)
                geolocator = Nominatim(user_agent="Emergency Bot")
                try:
                    location = geolocator.reverse(f"{latitude}, {longitude}")
                    st.session_state.address = location.address
                    st.success(f"Location received: {location.address}")
                    st.session_state.step = 'photos'
                    st.rerun()
                except:
                    st.error("Could not retrieve address from coordinates. Please provide additional details.")
                    st.session_state.step = 'address'
                    st.rerun()
        else:
            st.session_state.step = 'address'
            st.rerun()

    elif st.session_state.step == 'address':
        st.markdown("### Please provide your address:")
        address = st.text_area("Enter your complete address")
        
        if st.button("Submit Address"):
            st.session_state.address = address
            st.session_state.step = 'photos'
            st.rerun()

    elif st.session_state.step == 'photos':
        st.markdown("### Would you like to upload photos of the emergency situation?")
        uploaded_files = st.file_uploader("Choose photos", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
        
        if st.button("Continue"):
            if uploaded_files:
                st.session_state.photos = uploaded_files
            st.session_state.step = 'summary'
            st.rerun()

    elif st.session_state.step == 'summary':
        st.markdown("### Emergency Details Summary:")
        st.write(f"Emergency Type: {st.session_state.emergency_type}")
        
        emergency_details = {
            'type': st.session_state.emergency_type,
            'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if st.session_state.location:
            st.write(f"Location: {st.session_state.address}")
            st.write(f"Coordinates: {st.session_state.location}")
            emergency_details['location'] = st.session_state.address
            emergency_details['coordinates'] = st.session_state.location
        else:
            st.write(f"Address: {st.session_state.address}")
            emergency_details['address'] = st.session_state.address
        
        if st.session_state.photos:
            st.write(f"Number of photos uploaded: {len(st.session_state.photos)}")
        
        if not st.session_state.alert_sent:
            if st.button("Confirm and Send Emergency Alert"):
                with st.spinner("Sending emergency alert..."):
                    if send_emergency_alert_to_admin(emergency_details, st.session_state.photos):
                        st.session_state.alert_sent = True
                        st.success("Emergency alert sent! Please stay calm and wait for assistance.")
                        st.markdown("""
                        🚑 An ambulance has been dispatched to your location.
                        ⚠ Please stay calm and don't move the patient unless absolutely necessary.
                        👨‍⚕ Keep monitoring the patient's condition.
                        """)
                        st.session_state.step = 'chat'
                    else:
                        st.error("Failed to send emergency alert. Please try again.")
                st.rerun()

    # Chat interface (available at all steps after emergency type selection)
    if st.session_state.step != 'emergency_type':
        st.markdown("### Need immediate medical advice?")
        user_question = st.text_input("Type your medical emergency question here:")
        
        if user_question:
            response = get_gemini_response(user_question)
            st.session_state.chat_history.append(("user", user_question))
            st.session_state.chat_history.append(("bot", response))
        
        # Display chat history
        for role, message in st.session_state.chat_history:
            if role == "user":
                st.write(f"You: {message}")
            else:
                st.write(f"Bot: {message}")

if __name__ == "__main__":
    main()