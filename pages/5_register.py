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

st.set_page_config(
    page_title="sautAI",
    page_icon="🥘",
)

def register():
    st.title("Register")
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