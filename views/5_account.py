# activate.py
import streamlit as st
import requests
import os
from dotenv import load_dotenv
from utils import api_call_with_refresh, login_form, toggle_chef_mode
import datetime
import logging

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("error.log"),
    logging.StreamHandler()
])

load_dotenv()

# Content moved from main() to top level
try:
    # First check for special actions that should work WITHOUT login
    uid = st.query_params.get("uid", [""])
    token = st.query_params.get("token", [""])
    action = st.query_params.get("action", [""])
    
    # Handle account activation - this should work without login
    if uid and token and action == 'activate':
        st.title("Account Activation")
        st.info("Click the button below to activate your account.")
        if st.button("Activate Account", type="primary"):
            with st.spinner("Activating your account..."):
                response = api_call_with_refresh(
                    f'{os.getenv("DJANGO_URL")}/auth/api/register/verify-email/',
                    method='post',
                    data={'uid': uid, 'token': token},
                )
                if response.ok:
                    st.success(response.json()['message'])
                    # Show login form after successful activation
                    st.info("Your account has been activated! Please log in to continue.")
                    login_form()
                    st.stop()
                else:
                    st.error("Account activation failed: " + response.json()['message'])
                    st.stop()
    
    # Handle password reset - this should work without login
    if uid and token and action == 'password_reset':
        st.title("Reset Password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        if st.button("Reset Password"):
            # Check if new password and confirmation match
            if new_password != confirm_password:
                st.error("New password and confirmation do not match.")
                st.stop()

            # Define the URL
            url = f"{os.getenv('DJANGO_URL')}/auth/api/reset_password/"

            # Define the data
            data = {
                'uid': uid,
                'token': token,
                'new_password': new_password,
                'confirm_password': confirm_password
            }
            # Send the POST request
            response = api_call_with_refresh(url, method='post', data=data)

            # Check the response
            if response.status_code == 200:
                st.success("Password reset successfully.")
                st.info("Please log in with your new password.")
                login_form()
                st.stop()
            elif response.status_code == 400:
                st.error(response.json()['message'])
            elif response.status_code == 500:
                st.error("An error occurred while resetting the password.")
            else:
                st.error("Failed to reset password.")
            st.stop()
            
    # Now require login for everything else
    if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
        st.title("My Account")
        login_form()

        # Forgotten Password Form for Unauthenticated Users
        if action != 'password_reset' and action != 'activate':
            st.subheader("Forgot Password?")
            email = st.text_input("Email Address", "")
            if st.button("Send Reset Password Link"):
                # Define the URL
                url = f"{os.getenv('DJANGO_URL')}/auth/api/password_reset_request/"

                # Define the data
                data = {'email': email}

                # Send the POST request
                response = api_call_with_refresh(url, method='post', data=data)

                # Check the response
                if response.status_code == 200:
                    st.success("Reset password link sent successfully.")
                else:
                    st.error("Failed to send reset password link.")
        st.stop()
    
    # Rest of the account page for logged-in users
    # Logout Button
    if 'is_logged_in' in st.session_state and st.session_state['is_logged_in']:
        if st.button("Logout", key='form_logout'):
            # Clear session state but preserve navigation
            navigation_state = st.session_state.get("navigation", None)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            if navigation_state:
                st.session_state["navigation"] = navigation_state
            st.success("Logged out successfully!")
            st.rerun()
        # Call the toggle_chef_mode function
        toggle_chef_mode()

        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        if st.button("Change Password"):
            # Define the URL
            url = f"{os.getenv('DJANGO_URL')}/auth/api/change_password/"

            # Define the data
            data = {
                'current_password': current_password,
                'new_password': new_password,
                'confirm_password': confirm_password
            }

            # Send the POST request
            headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
            response = api_call_with_refresh(url, method='post', data=data, headers=headers)

            # Check the response
            if response.status_code == 200:
                st.success("Password changed successfully.")
            elif response.status_code == 400:
                st.error(response.json()['message'])
            elif response.status_code == 500:
                st.error("An error occurred while changing the password.")
            else:
                st.error("Failed to change password.")

except Exception as e:
    logging.error(f"An error occurred: {str(e)}")
    st.error("An unexpected error occurred. Please try again later.")
