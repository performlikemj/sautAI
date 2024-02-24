import json
from datetime import timedelta, datetime
from random import sample
from collections import defaultdict
import os
import openai
from openai import OpenAIError
import requests
import streamlit as st
import streamlit.components.v1 as components

# Define a function to get the user's access token
def refresh_token(refresh_token):
    refresh_response = requests.post(
        f'{os.getenv("DJANGO_URL")}/auth/api/token/refresh/', 
        json={'refresh': refresh_token}
    )
    print(f'refresh_response: {refresh_response}')
    return refresh_response.json() if refresh_response.status_code == 200 else None



# Use this in your API calls
def api_call_with_refresh(url, method='get', data=None, headers=None):
    response = requests.request(method, url, json=data, headers=headers)
    if response.status_code == 401:  # Token expired
        new_tokens = refresh_token(st.session_state.user_info["refresh"])
        if new_tokens:
            st.session_state.user_info.update(new_tokens)

            headers['Authorization'] = f'Bearer {new_tokens["access"]}'
            response = requests.request(method, url, json=data, headers=headers)  # Retry with new token
    return response

# Define a function to check if a user is authenticated
def is_user_authenticated():
    return 'user_info' in st.session_state and 'access' in st.session_state.user_info


def switch_user_role():
    # This function will call your Django backend to switch the user's role
    api_url = f"{os.getenv('DJANGO_URL')}/auth/api/switch_role/"
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
    response = api_call_with_refresh(api_url, method='post', headers=headers)
    return response.json() if response.status_code == 200 else None


def login_form():
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
            if response.status_code == 200:
                response_data = response.json()
                st.success("Logged in successfully!")
                # Update session state with user information
                st.session_state['user_info'] = response_data
                st.session_state['user_id'] = response_data['user_id']
                st.session_state['email_confirmed'] = response_data['email_confirmed']
                st.session_state['is_chef'] = response_data['is_chef']  # Include the is_chef attribute in the session state
                st.session_state['current_role'] = response_data['current_role']
                st.session_state['access_token'] = response_data['access']
                st.session_state['refresh_token'] = response_data['refresh']
                st.session_state['is_logged_in'] = True
                st.rerun()  # Rerun the script to reflect the login state
            else:
                st.error("Invalid username or password.")

        if register_button:
            st.switch_page("pages/5_register.py")

        # Password Reset Button
        if st.button("Forgot your password?"):
            # Directly navigate to the activate page for password reset
            st.switch_page("pages/4_account.py")


def toggle_chef_mode():
    # Ensure 'user_info' exists and contains 'is_chef'
    if 'user_info' in st.session_state and 'is_chef' in st.session_state['user_info']:
        
        # Use the value from 'user_info' for initial toggle state
        chef_mode = st.toggle("Switch Chef|Customer", value=st.session_state['user_info']['is_chef'], key="chef_mode_toggle")
        print(f'chef_mode: {chef_mode}')
        
        # Check if there's a change in the toggle state compared to 'user_info'
        if chef_mode != st.session_state['user_info']['is_chef']:
           
            # Call the backend to switch the user role
            result = switch_user_role()
            
            if result:  # If role switch is successful, update 'user_info' in session state
                st.session_state['user_info']['is_chef'] = chef_mode
                # Assuming 'result' contains the updated role information
                st.session_state['current_role'] = result['current_role']  # Update this based on actual response structure
                print(f"Role switched to: {st.session_state['current_role']}")  # Debug print
                st.rerun()
            else:
                # If role switch failed, revert the toggle to reflect actual user role
                st.error("Failed to switch roles.")
                st.session_state['user_info']['is_chef'] = not chef_mode  # Revert to original state
                st.rerun()

