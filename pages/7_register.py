import streamlit as st
import os
from dotenv import load_dotenv
import openai
import json
import re
import time
import requests
import pycountry
import datetime
import pytz
from utils import (api_call_with_refresh, login_form, toggle_chef_mode, 
                   fetch_and_update_user_profile, validate_input, parse_comma_separated_input)
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='history.log', # Log to a file. Remove this to log to console
                    filemode='w') # 'w' to overwrite the log file on each run, 'a' to append

def register():
            
    st.title("Register")
    st.write("Create an account.")

    try:
        with st.form(key='registration_form'):
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            phone_number = st.text_input("Phone Number")
            dietary_preferences = [ 'Everything', 'Vegetarian', 'Pescatarian', 'Gluten-Free', 'Keto', 'Paleo', 'Halal', 'Kosher', 'Low-Calorie', 'Low-Sodium', 'High-Protein', 'Dairy-Free', 'Nut-Free', 'Raw Food', 'Whole 30', 'Low-FODMAP', 'Diabetic-Friendly', 'Vegan']
            selected_dietary_preferences = st.multiselect("Dietary Preferences", dietary_preferences, default=[])
            custom_dietary_preferences_input = st.text_area(
                "Custom Dietary Preferences (comma separated)", 
                value='',
                help="Enter multiple custom dietary preferences separated by commas. Example: Paleo, Keto, Mediterranean"
            )            
            allergies = [
                'Peanuts', 'Tree nuts', 'Milk', 'Egg', 'Wheat', 'Soy', 'Fish', 'Shellfish', 'Sesame', 'Mustard', 
                'Celery', 'Lupin', 'Sulfites', 'Molluscs', 'Corn', 'Gluten', 'Kiwi', 'Latex', 'Pine Nuts', 
                'Sunflower Seeds', 'Poppy Seeds', 'Fennel', 'Peach', 'Banana', 'Avocado', 'Chocolate', 
                'Coffee', 'Cinnamon', 'Garlic', 'Chickpeas', 'Lentils'
            ]
            selected_allergies = st.multiselect("Allergies", allergies, default=[]) 
            custom_allergies = st.text_area("Custom Allergies (comma separated)", "")
            # Address fields
            st.subheader("Address")
            st.write("""
            Your address is used to:
            1. Find supported supermarkets in your area
            2. Find chefs in your area to provide meal planning meals
            """)
            street = st.text_input("Street")
            city = st.text_input("City")
            state = st.text_input("State/Province")
            postal_code = st.text_input("Postal Code")
            # Get a list of all countries
            countries = [country.name for country in pycountry.countries]
            selected_country = st.selectbox("Country", countries)
            # Convert the selected country to its two-letter country code
            country_code = pycountry.countries.get(name=selected_country).alpha_2

            # Define a dictionary for languages
            language_options = {
                'en': 'English',
                'ja': 'Japanese',
                'es': 'Spanish',
                'fr': 'French',
            }
            language_labels = list(language_options.values())
            language_keys = list(language_options.keys())
            preferred_language = st.selectbox("Preferred Language", language_labels, index=0)
            
            # Get the corresponding key for the selected value
            selected_language_code = language_keys[language_labels.index(preferred_language)]
                    
            # Time zone selection
            timezones = pytz.all_timezones
            selected_timezone = st.selectbox('Time Zone', options=timezones, index=timezones.index('UTC'))

            # Goal fields
            goal_name = st.text_input("Goal Name")
            goal_description = st.text_area("Goal Description")

            submit_button = st.form_submit_button(label='Register')
            if submit_button:
                valid_username, username_msg = validate_input(username, 'username')
                valid_email, email_msg = validate_input(email, 'email')
                valid_password, password_msg = validate_input(password, 'password')
                valid_phone, phone_msg = validate_input(phone_number, 'phone_number')
                valid_postal, postal_msg = validate_input(postal_code, 'postal_code')

                if not valid_username:
                    st.error(username_msg)
                elif not valid_email:
                    st.error(email_msg)
                elif not valid_password:
                    st.error(password_msg)
                elif not valid_phone:
                    st.error(phone_msg)
                elif not valid_postal:
                    st.error(postal_msg)
                else:
                    # Parse custom dietary preferences
                    custom_dietary_preferences = parse_comma_separated_input(custom_dietary_preferences_input)

                    user_data = {
                        "user": {
                            "username": username,
                            "email": email,
                            "password": password,
                            "phone_number": phone_number,
                            "dietary_preferences": selected_dietary_preferences,
                            "custom_dietary_preferences": custom_dietary_preferences,
                            "allergies": selected_allergies,
                            "custom_allergies": custom_allergies,
                            "timezone": selected_timezone,
                            "preferred_language": selected_language_code
                        },
                        "address": {
                            "street": street,
                            "city": city,
                            "state": state,
                            "country": country_code,
                            "postalcode": postal_code
                        },
                        "goal": {
                            "goal_name": goal_name,
                            "goal_description": goal_description
                        }
                    }

                    try:
                        with st.spinner("Registering your account..."):
                            api_url = f"{os.getenv('DJANGO_URL')}/auth/api/register/"
                            response = requests.post(api_url, json=user_data, timeout=10)
                        if response.status_code == 200:
                            st.success("Registration successful!")
                            st.info("Please check your email to activate your account.")
                            st.switch_page("sautai.py")
                        if response.status_code == 400:
                            errors = response.json().get('errors', {})
                            if isinstance(errors, dict):
                                for field, messages in errors.items():
                                    # Display the actual error message received from the backend
                                    st.error(f"{field}: {', '.join(messages)}")
                            else:
                                # Check for specific known issues before falling back to a generic error
                                st.error("An error occurred during registration. Please check your input and try again.")
                    except requests.exceptions.RequestException as e:
                        st.error("Failed to register due to a network issue. Please try again later.")
                        logging.error(f"Registration network error: {e}")
                    except Exception as e:
                        st.error("An unexpected error occurred during registration.")
                        logging.error(f"Unexpected error during registration: {e}")

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        st.error("An unexpected error occurred. Please try again later.")
                
if __name__ == "__main__":
    register()
