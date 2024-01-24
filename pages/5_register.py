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

st.set_page_config(
    page_title="sautAI",
    page_icon="🥘",
    layout="wide",
    initial_sidebar_state="collapsed",
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
        dietary_preferences = [ 'Vegan', 'Vegetarian', 'Pescatarian', 'Gluten-Free', 'Keto', 'Paleo', 'Halal', 'Kosher', 'Low-Calorie', 'Low-Sodium', 'High-Protein', 'Dairy-Free', 'Nut-Free', 'Raw Food', 'Whole 30', 'Low-FODMAP', 'Diabetic-Friendly', 'Everything']
        dietary_preference = st.selectbox("Dietary Preference", dietary_preferences)

        # Address fields
        st.subheader("Address")
        street = st.text_input("Street")
        city = st.text_input("City")
        state = st.text_input("State/Province")
        country = st.text_input("Country")
        postal_code = st.text_input("Postal Code")

        submit_button = st.form_submit_button(label='Register')
        if submit_button:
            if len(country) != 2 or not country.isalpha():
                st.error("Please enter a valid two-letter country code.")
            else:
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
                        "country": country,
                        "postalcode": postal_code
                    }
                }

                # API endpoint URL
                api_url = f"{os.getenv('DJANGO_URL')}/auth/api/register/"

                # Send the POST request to your Django API
                response = requests.post(api_url, json=user_data)

                if response.status_code == 200:
                    st.success("Registration successful!")
                    st.info("Please check your email to activate your account.")
                    
                else:
                    st.error("Registration failed. Please try again.")
                    # Handle errors (e.g., display error message)
    
if __name__ == "__main__":
    register()