# activate.py
import streamlit as st
import requests
import os
from dotenv import load_dotenv
from utils import api_call_with_refresh, login_form, toggle_chef_mode
import datetime

load_dotenv()

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

def activate_or_reset_password():
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
            
    # Assistant and other functionalities should not be shown if user is in chef mode
    if 'current_role' in st.session_state and st.session_state['current_role'] != 'chef':
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
