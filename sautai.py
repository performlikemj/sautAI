# sautai.py is the main file that runs the Streamlit app.
import streamlit as st
import requests
from dotenv import load_dotenv
import os
import datetime
import logging
from utils import login_form, toggle_chef_mode, validate_input

# Load environment variables and configure logging
load_dotenv()
logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='app.log', filemode='w')

logging.info("Starting the Streamlit app")

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

assistant = st.Page("pages/1_assistant.py", title="sautAI Assistant", icon="🥘")
history = st.Page("pages/2_history.py", title="Meal History", icon="📜")
plans = st.Page("pages/6_meal_plans.py", title="Meal Plans", icon="🍽️")
account = st.Page("pages/4_account.py", title="My Account", icon="👤")
register = st.Page("pages/5_register.py", title="Register", icon="📝")
profile = st.Page("pages/3_profile.py", title="Profile", icon="📋")



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
                    if validate_input(username, 'username') and validate_input(password, 'password'):
                        try:
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
                                st.switch_page("pages/1_assistant.py")  # Rerun the script to reflect the login state
                            else:
                                st.error("Invalid username or password.")
                        except requests.exceptions.HTTPError as http_err:
                            st.error("Invalid username or password.")
                            logging.warning(f"Login failed: {http_err}")
                        except requests.exceptions.RequestException as req_err:
                            st.error("Unable to connect to the server. Please try again later.")
                            logging.error(f"Connection error: {req_err}")
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
            # Call the toggle_chef_mode function
            toggle_chef_mode()
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
                At sautAI, we believe that the key to a healthier life lies in preparation. Our app is designed to remove 
                the friction from healthy eating by providing you with the tools and resources needed to plan, prepare, and 
                enjoy nutritious meals effortlessly.
                
                sautAI is your companion in the journey towards a healthier lifestyle. Whether you're looking to maintain a 
                balanced diet, meet specific dietary needs, or simply explore new and nutritious meal options, sautAI has you covered. 
                We offer:
                """
            )
            st.write(
                """
                - **Personalized Meal Planning:** Get tailored meal plans based on your dietary preferences and health goals. 
                  With sautAI, planning your meals is both simple and enjoyable.
                - **Health and Wellness Tracking:** Monitor your progress with tools that help you stay on track with your nutrition and fitness goals.
                - **Dietary Management:** Easily manage dietary restrictions and preferences. sautAI makes it easy to navigate your needs, ensuring you always have the best meal options available.
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
        
        # Call to Action Section
        with st.container():
            st.write("## Join sautAI Today")
            st.write("Are you ready to take control of your health? Join sautAI and start your journey towards a healthier, happier you. Whether you're preparing your own meals or connecting with local chefs for convenience, sautAI is here to support your goals.")
            if st.button("Sign Up Now"):
                # Redirect or perform an action for registration
                st.switch_page("pages/5_register.py")

    except Exception as e:
        st.error("Error occurred. We're looking into it.")
        logging.error("Error occurred", exc_info=True) 

if __name__ == "__main__":
    main()