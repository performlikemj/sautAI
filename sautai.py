# main.py
import streamlit as st
import requests
from dotenv import load_dotenv
load_dotenv()
import os
from extra_streamlit_components import CookieManager
import datetime



load_dotenv()


st.set_page_config(
    page_title="sautAI",
    page_icon="🥘",
    layout="wide",
    initial_sidebar_state="auto",
)

cookie_manager = CookieManager()


def main():

    # Login Form
    if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
        with st.form(key='login_form'):
            st.header("Login")
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
                    expires_at = datetime.datetime.now() + datetime.timedelta(days=1)
                    cookie_manager.set("access_token", response_data['access'], expires_at=expires_at, key='access_token')
                    st.session_state['is_logged_in'] = True
                    st.switch_page("pages/1_assistant.py")
                else:
                    st.error("Invalid username or password.")
            if register_button:
                st.switch_page("pages/5_register.py")
                   
    
    print("Cookie value after set:", cookie_manager.get('access_token'))


    # Logout Button
    if 'is_logged_in' in st.session_state and st.session_state['is_logged_in']:
        if st.button("Logout", key='form_logout'):
            cookie_manager.delete('access_token')
            # Clear session state as well
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("Logged out successfully!")
            print("Cookie value after delete:", cookie_manager.get('access_token'))
            st.rerun()
        sidebar_logout()

    # Hero Page
    st.markdown("""
        <div style="text-align: center;">
            <h1>More Time. More Health.</h1>
            <p>Discover how our service can enhance your lifestyle.</p>
        </div>
        """, unsafe_allow_html=True)
        
def sidebar_logout():
    if st.sidebar.button("Logout", key='sidebar_logout'):
        cookie_manager.delete('access_token')
        # Clear session state as well
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("Logged out successfully!")
        print("Cookie value after delete:", cookie_manager.get('access_token'))
        st.rerun()


if __name__ == "__main__":
    main()
