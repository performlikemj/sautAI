# sautai.py is the main file that runs the Streamlit app.
import streamlit as st
import requests
from dotenv import load_dotenv
import os
import datetime
import logging

# Load environment variables and configure logging
load_dotenv()
logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='app.log', filemode='w')

logging.info("Starting the Streamlit app")

def main():
    try:
        # Login Form
        if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:


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


        # Logout Button
        if 'is_logged_in' in st.session_state and st.session_state['is_logged_in']:
            if st.button("Logout", key='form_logout'):
                # Clear session state as well
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.success("Logged out successfully!")
                st.rerun()

        # Hero Page
        st.markdown("""
            <div style="text-align: center;">
                <h1>More Time. More Health.</h1>
                <p>Discover how our service can enhance your lifestyle.</p>
            </div>
            """, unsafe_allow_html=True)
    except Exception as e:
        st.error("Error occurred. We're looking into it.")
        logging.error("Error occurred", exc_info=True)  # Logs the error with traceback

if __name__ == "__main__":
    main()
