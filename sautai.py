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

st.set_page_config(
    page_title="sautAI - Your Diet and Nutrition Guide",
    page_icon="🥗", 
    initial_sidebar_state="expanded",
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

def main():
    try:
        # Login Form
        if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
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

        # Hero Section
        st.markdown("""
            <div style="text-align: center;">
                <h1>Welcome to sautAI</h1>
                <p>Your Personal Diet and Nutrition Guide</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Introduction Section
        with st.container():
            st.write("## Discover sautAI")
            st.write(
                """
                sautAI is designed to empower you on your journey towards achieving your health and wellness goals. 
                Through a comprehensive suite of features, sautAI helps you explore nutritious meal options, 
                connect with expert chefs, and manage your dietary needs effectively. Let's dive into how sautAI 
                can enhance your lifestyle.
                """
            )
        
        # Features Section
        with st.expander("Explore Our Features"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.image("https://live.staticflickr.com/65535/53502731882_3c40de9d35_b.jpg", caption="Personalized Meal Plans", use_column_width=True)
            with col2:
                st.image("https://live.staticflickr.com/65535/53503924179_28ed5b65c6_b.jpg", caption="Health and Wellness Tracking", use_column_width=True)
            with col3:
                st.image("https://live.staticflickr.com/65535/53503924239_cfbdefb816_b.jpg", caption="Dietary Management", use_column_width=True)
        
        # How It Works Section
        with st.container():
            st.write("## How It Works")
            st.write(
                """
                - **Step 1:** Register and set your dietary preferences and health goals.
                - **Step 2:** Discover and select meals that align with your preferences.
                - **Step 3:** Customize and approve your weekly meal plans.
                - **Step 4:** Track your progress and adjust your plans as needed.
                """
            )
        
        # # Testimonials Section
        # with st.container():
        #     st.write("## What Our Users Say")
        #     tab1, tab2 = st.tabs(["User 1", "User 2"])
        #     with tab1:
        #         st.write("sautAI has transformed the way I approach meal planning and nutrition.")
        #     with tab2:
        #         st.write("Thanks to sautAI, I'm eating healthier, feeling better, and enjoying delicious meals.")
        
        # Call to Action Section
        with st.container():
            st.write("## Ready to Start?")
            st.write("Join sautAI today and take the first step towards a healthier, happier you.")
            if st.button("Sign Up Now"):
                # Redirect or perform an action for registration
                st.switch_page("pages/5_register.py")

    except Exception as e:
        st.error("Error occurred. We're looking into it.")
        logging.error("Error occurred", exc_info=True)  # Logs the error with traceback

if __name__ == "__main__":
    main()