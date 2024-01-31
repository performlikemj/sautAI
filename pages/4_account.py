# activate.py
import streamlit as st
import requests
import os
from dotenv import load_dotenv
from utils import api_call_with_refresh

load_dotenv()

def activate_or_reset_password():
    st.title("Account Management")

    # Password Reset Form for Unauthenticated Users
    uid = st.query_params.get("uid", [""])
    token = st.query_params.get("token", [""])
    action = st.query_params.get("action", [""])

    if uid and token and action == 'password_reset':
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        if st.button("Reset Password"):
            # Check if new password and confirmation match
            if new_password != confirm_password:
                st.error("New password and confirmation do not match.")
                return

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
                st.switch_page("sautai.py")
            elif response.status_code == 400:
                st.error(response.json()['message'])
            elif response.status_code == 500:
                st.error("An error occurred while resetting the password.")
            else:
                st.error("Failed to reset password.")

    # Account Activation Logic
    if uid and token and action == 'activate':
        if st.button("Activate Account"):
            with st.spinner("Activating..."):
                response = api_call_with_refresh(
                    f'{os.getenv("DJANGO_URL")}/auth/api/register/verify-email/',
                    method='post',
                    data={'uid': uid, 'token': token},
                )
                if response.ok:
                    st.success(response.json()['message'])
                    st.switch_page("sautai.py")
                else:
                    st.error("Account activation failed: " + response.json()['message'])

    # Forgotten Password Form for Unauthenticated Users
    if action != 'password_reset' and action != 'activate':
        if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
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

    # Change Password Form for Authenticated Users
    if 'is_logged_in' in st.session_state and st.session_state['is_logged_in']:
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

if __name__ == "__main__":
    activate_or_reset_password()
