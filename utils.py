import json
from datetime import timedelta, datetime
from random import sample
from collections import defaultdict
import os
import openai
from openai import OpenAIError
import requests
import streamlit as st

# Define a function to get the user's access token
def refresh_token(refresh_token):
    refresh_response = requests.post(
        f'{os.getenv("DJANGO_URL")}/auth/api/token/refresh/', 
        json={'refresh': refresh_token}
    )
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
                st.session_state['timezone'] = response_data['timezone']
                st.session_state['preferred_language'] = response_data['preferred_language']
                st.session_state['dietary_preference'] = response_data['dietary_preference']
                st.session_state['custom_dietary_preference'] = response_data['custom_dietary_preference']
                st.session_state['allergies'] = response_data['allergies']
                st.session_state['custom_allergies'] = response_data['custom_allergies']
                st.session_state['goal_name'] = response_data['goal_name']
                st.session_state['goal_description'] = response_data['goal_description']
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

def fetch_and_update_user_profile():
    if is_user_authenticated():
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}

        # Fetch user details
        user_response = api_call_with_refresh(f'{os.getenv("DJANGO_URL")}/auth/api/user_details/', headers=headers)
        if user_response.status_code == 200:
            user_data = user_response.json()
            st.session_state['user_id'] = user_data['id']
            st.session_state['email_confirmed'] = user_data['email_confirmed']
            st.session_state['is_chef'] = user_data.get('is_chef', False)
            st.session_state['timezone'] = user_data['timezone']
            st.session_state['preferred_language'] = user_data['preferred_language']
            st.session_state['dietary_preference'] = user_data['dietary_preference']
            st.session_state['custom_dietary_preference'] = user_data['custom_dietary_preference']
            st.session_state['allergies'] = user_data['allergies']
            st.session_state['custom_allergies'] = user_data['custom_allergies']
            st.session_state['goal_name'] = user_data['goals']['goal_name'] if user_data.get('goals') else ""
            st.session_state['goal_description'] = user_data['goals']['goal_description'] if user_data.get('goals') else ""
            st.session_state['current_role'] = user_data.get('current_role', '')
        else:
            st.error("Failed to fetch user profile.")

        # Fetch address details
        address_response = api_call_with_refresh(f'{os.getenv("DJANGO_URL")}/auth/api/address_details/', headers=headers)
        if address_response.status_code == 200:
            address_data = address_response.json()
            st.session_state['address'] = {
                'street': address_data.get('street', ''),
                'city': address_data.get('city', ''),
                'state': address_data.get('state', ''),
                'postalcode': address_data.get('input_postalcode', ''),
                'country': address_data.get('country', '')
            }
        else:
            st.error("Failed to fetch address details.")

def toggle_chef_mode():
    # Ensure 'user_info' exists, contains 'is_chef', and user is authorized as a chef
    if 'user_info' in st.session_state and st.session_state['user_info'].get('is_chef', False):
        
        # Display the toggle only if the user is authorized to be a chef
        chef_mode = st.toggle("Switch Chef | Customer", value=st.session_state['user_info'].get('current_role') == 'chef', key="chef_mode_toggle")
            
        # Check if there's a change in the toggle state compared to 'user_info'
        if ((chef_mode and st.session_state['user_info']['current_role'] != 'chef') or
            (not chef_mode and st.session_state['user_info']['current_role'] != 'customer')):
           
            # Call the backend to switch the user role
            result = switch_user_role()
            
            if result:  # If role switch is successful, update 'user_info' in session state
                # Assuming 'result' properly reflects the updated role
                new_role = 'chef' if chef_mode else 'customer'
                st.session_state['current_role'] = new_role
                st.session_state['user_info']['current_role'] = new_role
                st.rerun()
            else:
                # If role switch failed, inform the user and revert the toggle to reflect actual user role
                st.error("Failed to switch roles.")
                # No need to rerun here; just display the error message and keep the state consistent
