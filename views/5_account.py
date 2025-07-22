# activate.py
import streamlit as st
import requests
import os
from dotenv import load_dotenv
from utils import api_call_with_refresh, login_form, toggle_chef_mode, footer
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
    
    # Handle immediate email processing - this should work without login
    if token and action == 'process_now':
        st.title("Process Email Now")
        st.info("Processing your email message immediately...")
        
        try:
            with st.spinner("Processing your message..."):
                # Call the API to trigger immediate processing
                response = requests.get(
                    f'{os.getenv("DJANGO_URL")}/auth/api/process_now/',
                    json={'token': token},
                )
            
            if response and response.ok:
                result = response.json()
                if result.get('status') == 'success':
                    st.success("✅ " + result.get('message', 'Your message has been processed successfully!'))
                    st.info("You should receive a response from your assistant shortly.")
                else:
                    st.warning("⚠️ " + result.get('message', 'Your message was processed but there may have been an issue.'))
            else:
                error_data = response.json() if response else {}
                error_msg = error_data.get('message', 'Unknown error occurred')
                st.error(f"❌ Failed to process your message: {error_msg}")
                
        except Exception as e:
            st.error(f"❌ An error occurred while processing your message: {str(e)}")
            
        st.markdown("---")
        st.markdown("**Need to send another message?** Simply reply to any email from your assistant.")
        st.markdown("**Want the full experience?** [Log in to your dashboard](/) for more features.")
        st.stop()
    
    # Handle account activation - this should work without login
    if uid and token and action == 'activate':
        st.title("Account Activation")
        st.info("Activating your account...")
        with st.spinner("Activating your account..."):
            response = api_call_with_refresh(
                f'{os.getenv("DJANGO_URL")}/auth/api/register/verify-email/',
                method='post',
                data={'uid': uid, 'token': token},
            )
        if response and response.ok:
            st.success(response.json()['message'])
            # Show login form after successful activation
            st.info("Your account has been activated! Please log in to continue.")
            login_form()
            st.switch_page("home")
        else:
            error_msg = response.json().get('message') if response else 'Unknown error'
            st.error("Account activation failed: " + error_msg)
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
        st.title("Account")
        
        # Create tabs for better organization
        tab1, tab2 = st.tabs(["Login", "Reset Password"])
        
        with tab1:
            st.subheader("Login to Your Account")
            login_form()

        with tab2:
            # Forgotten Password Form for Unauthenticated Users
            if action != 'password_reset' and action != 'activate':
                st.subheader("Reset Your Password")
                st.write("Enter your email address and we'll send you a link to reset your password.")
                
                with st.form("password_reset_form"):
                    email = st.text_input("Email Address", placeholder="Enter your email address")
                    submit_button = st.form_submit_button("Send Reset Link", type="primary")
                    
                    if submit_button and email:
                        # Define the URL
                        url = f"{os.getenv('DJANGO_URL')}/auth/api/password_reset_request/"

                        # Define the data
                        data = {'email': email}

                        # Send the POST request
                        response = api_call_with_refresh(url, method='post', data=data)

                        # Check the response
                        if response.status_code == 200:
                            st.success("✅ Reset password link sent successfully! Please check your email.")
                            st.info("If you don't see the email in your inbox, please check your spam folder.")
                        else:
                            st.error("❌ Failed to send reset password link. Please check your email address and try again.")
                    elif submit_button and not email:
                        st.error("Please enter your email address.")
        st.stop()
    
    # Rest of the account page for logged-in users
    st.title("My Account")
    
    # User info section
    if st.session_state.get('user_info'):
        user_info = st.session_state['user_info']
        st.success(f"👋 Welcome back, {user_info.get('username', 'User')}!")
    
    # Account management tabs for logged-in users
    account_tab1, account_tab2 = st.tabs(["Account Settings", "Change Password"])
    
    with account_tab1:
        # Logout Button
        if st.button("🚪 Logout", type="secondary"):
            # Clear session state but preserve navigation
            navigation_state = st.session_state.get("navigation", None)
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            if navigation_state:
                st.session_state["navigation"] = navigation_state
            st.success("Logged out successfully!")
            st.rerun()
    
    with account_tab2:
        st.subheader("Change Your Password")
        st.write("Enter your current password and choose a new one.")
        
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            submit_button = st.form_submit_button("Change Password", type="primary")
            
            if submit_button:
                if not all([current_password, new_password, confirm_password]):
                    st.error("Please fill in all fields.")
                elif new_password != confirm_password:
                    st.error("New password and confirmation do not match.")
                else:
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
                        st.success("✅ Password changed successfully!")
                    elif response.status_code == 400:
                        st.error(f"❌ {response.json().get('message', 'Failed to change password.')}")
                    elif response.status_code == 500:
                        st.error("❌ An error occurred while changing the password.")
                    else:
                        st.error("❌ Failed to change password.")

except Exception as e:
    logging.error(f"An error occurred: {str(e)}")
    st.error("An unexpected error occurred. Please try again later.")

footer()
