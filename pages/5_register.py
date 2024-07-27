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
from utils import api_call_with_refresh, login_form, toggle_chef_mode, fetch_and_update_user_profile

st.set_page_config(
    page_title="sautAI - Your Diet and Nutrition Guide",
    page_icon="🥗", 
    initial_sidebar_state="auto",
    menu_items={
        'Report a bug': "mailto:support@sautai.com",
        'About': """
        # Welcome to sautAI 🥗
        
        **sautAI** is your personal diet and nutrition assistant, designed to empower you towards achieving your health and wellness goals. Here's what makes sautAI special:

        - **Diverse Meal Discoveries**: Explore a vast database of dishes and meet talented chefs. Whether you're craving something specific or looking for inspiration, sautAI connects you with the perfect meal solutions.
        
        - **Customized Meal Planning**: Get personalized weekly meal plans that cater to your dietary preferences and nutritional needs. With sautAI, planning your meals has never been easier or more exciting.
        
        - **Ingredient Insights**: Navigate dietary restrictions with ease. Search for meals by ingredients or exclude specific ones to meet your dietary needs.
        
        - **Interactive Meal Management**: Customize your meal plans by adding, removing, or replacing meals. sautAI makes it simple to adjust your plan on the fly.
        
        - **Feedback & Reviews**: Share your culinary experiences and read what others have to say. Your feedback helps us refine and enhance the sautAI experience.
        
        - **Health & Wellness Tracking**: Monitor your health metrics, set and update goals, and receive tailored nutrition advice. sautAI is here to support your journey towards a healthier lifestyle.
        
        - **Local Supermarket Finder**: Discover supermarkets near you offering healthy meal options. Eating healthy is now more convenient than ever.
        
        - **Allergy & Dietary Alerts**: Stay informed about potential allergens in your meals. sautAI prioritizes your health and safety.
        
        Discover the joy of healthy eating and seamless meal planning with **sautAI**. Let's embark on this journey together.

        ### Stay Connected
        Have questions or feedback? Contact us at [support@sautai.com](mailto:support@sautai.com).

        Follow us on our journey:
        - [Instagram](@sautAI_official)
        - [Twitter](@sautAI_official)
        - [Report a Bug](mailto:support@sautai.com)
        """
    }
)

def register():
    # Login Form
    if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
        login_form()

    # Logout Button
    if 'is_logged_in' in st.session_state and st.session_state['is_logged_in']:
        if st.button("Logout", key='form_logout'):
            # Clear session state as well
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("Logged out successfully!")
            st.rerun()
        # Call the toggle_chef_mode function
        toggle_chef_mode()
            
    else:
        st.title("Register")
        st.write("Create an account.")

        with st.form(key='registration_form'):
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            phone_number = st.text_input("Phone Number")
            dietary_preferences = [ 'Everything', 'Vegetarian', 'Pescatarian', 'Gluten-Free', 'Keto', 'Paleo', 'Halal', 'Kosher', 'Low-Calorie', 'Low-Sodium', 'High-Protein', 'Dairy-Free', 'Nut-Free', 'Raw Food', 'Whole 30', 'Low-FODMAP', 'Diabetic-Friendly', 'Vegan']
            dietary_preference = st.selectbox("Dietary Preference", dietary_preferences)
            custom_dietary_preference = st.text_input("Custom Dietary Preference (if not listed above)", "")
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
                # Construct the data payload for the API request
                user_data = {
                    "user": {
                        "username": username,
                        "email": email,
                        "password": password,
                        "phone_number": phone_number,
                        "dietary_preference": dietary_preference,
                        "custom_dietary_preference": custom_dietary_preference,
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

                # API endpoint URL
                api_url = f"{os.getenv('DJANGO_URL')}/auth/api/register/"
                # Send the POST request to your Django API
                response = requests.post(api_url, json=user_data)

                if response.status_code == 200:
                    st.success("Registration successful!")
                    st.info("Please check your email to activate your account.")
                    st.switch_page("sautai.py")
                elif response.status_code == 400:
                    errors = response.json().get('errors', {})
                    if 'username' in errors:
                        st.error(errors['username'][0])
                    elif 'email' in errors:
                        st.error("A user with that information already exists.")
                else:
                    st.error("Registration failed. Please try again.")
    
if __name__ == "__main__":
    register()
