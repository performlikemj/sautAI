# pages/register.py
import streamlit as st
import os
from dotenv import load_dotenv
import openai
import os
import json
import re
import time
import requests
from openai import OpenAIError
import pycountry
import datetime

st.set_page_config(
    page_title="sautAI - Your Diet and Nutrition Guide",
    page_icon="🥗", 
    initial_sidebar_state="expanded",
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
    st.title("Register")

    if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
        with st.expander("Login", expanded=False):
            st.write("Login to your account.")
            with st.form(key='login_form'):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit_button = st.form_submit_button(label='Login')
                register_button = st.form_submit_button(label="Register")

            if submit_button:
                # Remove guest user from session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                # API call to get the token
                response = requests.post(
                    f'{os.getenv("DJANGO_URL")}/auth/api/login/',
                    json={'username': username, 'password': password}
                )
                print(response)
                if response.status_code == 200:
                    response_data = response.json()
                    st.success("Logged in successfully!")
                    st.session_state['user_info'] = response_data
                    st.session_state['user_id'] = response_data['user_id']
                    st.session_state['email_confirmed'] = response_data['email_confirmed']
                    # Set cookie with the access token
                    st.session_state['access_token'] = response_data['access']
                    # Set cookie with the refresh token
                    st.session_state['refresh_token'] = response_data['refresh']
                    expires_at = datetime.datetime.now() + datetime.timedelta(days=1)
                    st.session_state['is_logged_in'] = True
                    st.switch_page("pages/1_assistant.py")
                else:
                    st.error("Invalid username or password.")
            if register_button:
                st.switch_page("pages/5_register.py")
                    

            # Password Reset Button
            if st.button("Forgot your password?"):
                # Directly navigate to the activate page for password reset
                st.switch_page("pages/4_account.py")

    st.header("Register")
    st.write("Create an account.")


    with st.form(key='registration_form'):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        phone_number = st.text_input("Phone Number")
        dietary_preferences = [ 'Everything', 'Vegetarian', 'Pescatarian', 'Gluten-Free', 'Keto', 'Paleo', 'Halal', 'Kosher', 'Low-Calorie', 'Low-Sodium', 'High-Protein', 'Dairy-Free', 'Nut-Free', 'Raw Food', 'Whole 30', 'Low-FODMAP', 'Diabetic-Friendly', 'Vegan']
        dietary_preference = st.selectbox("Dietary Preference", dietary_preferences)

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
        submit_button = st.form_submit_button(label='Register')
        if submit_button:
            # Construct the data payload for the API request
            user_data = {
                "user": {
                    "username": username,
                    "email": email,
                    "password": password,
                    "phone_number": phone_number,
                    "dietary_preference": dietary_preference
                },
                "address": {
                    "street": street,
                    "city": city,
                    "state": state,
                    "country": country_code,
                    "postalcode": postal_code
                }
            }

            # API endpoint URL
            api_url = f"{os.getenv('DJANGO_URL')}/auth/api/register/"
            print(f'api_url: {api_url}')
            # Send the POST request to your Django API
            response = requests.post(api_url, json=user_data)

            if response.status_code == 200:
                st.success("Registration successful!")
                st.info("Please check your email to activate your account.")
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