import streamlit as st
import requests
from dotenv import load_dotenv
import os
import datetime
import logging
from utils import login_form, toggle_chef_mode, validate_input, footer, fetch_and_update_user_profile

# Load environment variables and configure logging
load_dotenv()
logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='app.log', filemode='w')

logging.info("Starting the Streamlit app")

# Content moved from main() to top level
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
                            if key != "navigation":  # Preserve navigation state
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
                            st.switch_page("views/1_assistant.py")  # Navigate to assistant page after login
                        else:
                            st.error("Invalid username or password.")
                    except requests.exceptions.HTTPError as http_err:
                        st.error("Invalid username or password.")
                        logging.warning(f"Login failed: {http_err}")
                    except requests.exceptions.RequestException as req_err:
                        st.error("Unable to connect to the server. Please try again later.")
                        logging.error(f"Connection error: {req_err}")
            if register_button:
                st.switch_page("views/7_register.py")

            # Password Reset Button
            if st.button("Forgot your password?"):
                st.switch_page("views/5_account.py")

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
        
    # Hero Section with improved layout and copy and responsive design
    # Add custom CSS for responsive layout
    st.markdown("""
    <style>
    .responsive-container {
        width: 100%;
        display: flex;
        flex-direction: column;
    }
    
    .hero-image {
        max-width: 100%;
        height: auto;
        margin-bottom: 20px;
    }
    
    @media (min-width: 768px) {
        .responsive-container {
            flex-direction: row;
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Use container for more control over layout
    with st.container():
        # For larger screens, use columns
        if st.session_state.get('_is_desktop', True):  # Default to desktop view
            hero_col1, hero_col2 = st.columns([0.6, 0.4])
            
            with hero_col1:
                st.markdown("""
                    <h1 style="color: #5cb85c;">Connect With Local Chefs</h1>
                    <p style="font-size: 1.2rem;">We link you with talented cooks in your community—from chefs preserving family recipes to those creating new flavors. Our AI simply helps plan your meals.</p>
                    """, unsafe_allow_html=True)
                
                if st.button("Get Started Today 🍽️", use_container_width=True):
                    st.switch_page("views/7_register.py")
            
            with hero_col2:
                st.markdown("""
                <div style="padding: 10px;">
                    <img src="https://live.staticflickr.com/65535/54548860874_7569d1dbdc_b.jpg" class="hero-image">
                </div>
                """, unsafe_allow_html=True)
        else:
            # For mobile/smaller screens, stack vertically
            st.markdown("""
                <div class="responsive-container">
                    <div>
                        <h1 style="color: #5cb85c;">Connect With Local Chefs</h1>
                        <p style="font-size: 1.2rem;">We link you with talented cooks in your community—from chefs preserving family recipes to those creating new flavors. Our AI simply helps plan your meals.</p>
                    </div>
                    <div>
                        <img src="https://live.staticflickr.com/65535/54548860874_7569d1dbdc_b.jpg" class="hero-image">
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            if st.button("Get Started Today 🍽️", use_container_width=True):
                st.switch_page("views/7_register.py")
    
    st.markdown("---")  # Divider for visual separation
    
    # Introduction Section with clearer structure
    st.markdown("<h2 style='text-align: center;'>Why sautAI?</h2>", unsafe_allow_html=True)
    
    intro_col1, intro_col2, intro_col3 = st.columns(3)
    

    with intro_col1:
        st.markdown("### 🥘 Local Connection")
        st.markdown("""
        Discover chefs in your neighborhood who prepare traditional favorites and exciting new meals while keeping culinary traditions alive.
        """)
    
    with intro_col2:
        st.markdown("### 🧠 AI Meal Planning")
        st.markdown("""
        Let our AI suggest balanced meal plans so you can focus on enjoying food and community.
        """)
    
    with intro_col3:
        st.markdown("### 🥦 Health Tracking")
        st.markdown("""
        Monitor your progress, track calories, and watch your health metrics improve with every meal.
        """)
    
    st.markdown("---")
    
    # Features Section with more visual appeal and responsive design
    st.markdown("<h2 style='text-align: center;'>How sautAI Works For You</h2>", unsafe_allow_html=True)
    
    # For responsive features section, check if we're on desktop or mobile
    if st.session_state.get('_is_desktop', True):
        # Desktop view - use tabs
        features_tab1, features_tab2, features_tab3 = st.tabs(["Meal Planning", "Health Tracking", "Expert Support"])
        
        with features_tab1:
            col1, col2 = st.columns([0.4, 0.6])
            with col1:
                st.image("https://live.staticflickr.com/65535/54550764768_d565973881_b.jpg", use_container_width=True)
            with col2:
                st.markdown("### Effortless Meal Planning")
                st.markdown("""
                - **Customized Weekly Plans** – Get a full week of meals tailored to your diet and preferences
                - **Ingredient Awareness** – Avoid allergens and disliked foods automatically
                - **One-Click Adjustments** – Swap meals you don't like with alternatives in seconds
                - **Chef Connections** – Connect with local chefs for healthy meal preparation—from inventive new dishes to cherished classics
                """)
        
        with features_tab2:
            col1, col2 = st.columns([0.4, 0.6])
            with col1:
                st.image("https://live.staticflickr.com/65535/54550711849_2ac8954256_b.jpg", use_container_width=True)
            with col2:
                st.markdown("### Simple Health Monitoring")
                st.markdown("""
                - **Calorie & Nutrition Tracking** – Effortlessly log and monitor your daily intake
                - **Progress Visualization** – See your health journey with clear, intuitive charts
                - **Mood & Energy Monitoring** – Track how foods affect your well-being
                - **Goal Setting** – Set achievable targets and watch yourself reach them
                """)
        
        with features_tab3:
            col1, col2 = st.columns([0.4, 0.6])
            with col1:
                st.image("https://live.staticflickr.com/65535/54549653432_73f6b0bdfd_b.jpg", use_container_width=True)
            with col2:
                st.markdown("### Ongoing Support")
                st.markdown("""
                - **AI Nutrition Assistant** – Get immediate answers to all your nutrition questions
                - **Personalized Recommendations** – Receive suggestions that improve over time
                - **Emergency Supply Planning** – Be prepared with healthy options for unexpected situations
                - **Community Connection** – Learn from others on similar health journeys
                """)
    else:
        # Mobile view - stack everything vertically with expanders
        with st.expander("Meal Planning", expanded=True):
            st.image("https://live.staticflickr.com/65535/53502731882_3c40de9d35_b.jpg", use_container_width=True)
            st.markdown("### Effortless Meal Planning")
            st.markdown("""
            - **Customized Weekly Plans** – Get a full week of meals tailored to your diet and preferences
            - **Ingredient Awareness** – Avoid allergens and disliked foods automatically
            - **One-Click Adjustments** – Swap meals you don't like with alternatives in seconds
            - **Chef Connections** – Connect with local chefs for healthy meal preparation—from inventive new dishes to cherished classics
            """)
            
        with st.expander("Health Tracking", expanded=False):
            st.image("https://live.staticflickr.com/65535/53503924179_28ed5b65c6_b.jpg", use_container_width=True)
            st.markdown("### Simple Health Monitoring")
            st.markdown("""
            - **Calorie & Nutrition Tracking** – Effortlessly log and monitor your daily intake
            - **Progress Visualization** – See your health journey with clear, intuitive charts
            - **Mood & Energy Monitoring** – Track how foods affect your well-being
            - **Goal Setting** – Set achievable targets and watch yourself reach them
            """)
            
        with st.expander("Expert Support", expanded=False):
            st.image("https://live.staticflickr.com/65535/53503924239_cfbdefb816_b.jpg", use_container_width=True)
            st.markdown("### Ongoing Support")
            st.markdown("""
            - **AI Nutrition Assistant** – Get immediate answers to all your nutrition questions
            - **Personalized Recommendations** – Receive suggestions that improve over time
            - **Emergency Supply Planning** – Be prepared with healthy options for unexpected situations
            - **Community Connection** – Learn from others on similar health journeys
            """)
    
    st.markdown("---")
    
    # How It Works Section with clearer steps and responsive design
    st.markdown("<h2 style='text-align: center;'>Simple Steps to Better Health</h2>", unsafe_allow_html=True)
    
    # Responsive steps section
    if st.session_state.get('_is_desktop', True):
        # Desktop view - use 4 columns
        steps_col1, steps_col2, steps_col3, steps_col4 = st.columns(4)
        
        with steps_col1:
            st.markdown("### 1️⃣ Sign Up")
            st.markdown("Create your profile and tell us about your dietary needs and health goals.")
        
        with steps_col2:
            st.markdown("### 2️⃣ Get Your Plan")
            st.markdown("Receive customized meal plans that match your preferences and nutritional requirements.")
        
        with steps_col3:
            st.markdown("### 3️⃣ Track Progress")
            st.markdown("Log your meals and health metrics to monitor your journey toward better health.")
        
        with steps_col4:
            st.markdown("### 4️⃣ Adjust & Improve")
            st.markdown("Refine your plans based on what works for you with the help of our AI assistant.")
    else:
        # Mobile view - use 2 columns with 2 rows
        st.markdown("""
        <style>
        .step-container {
            margin-bottom: 20px;
            padding: 10px;
            border-radius: 5px;
            background-color: #f8f9fa;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="step-container">
            <h3>1️⃣ Sign Up</h3>
            <p>Create your profile and tell us about your dietary needs and health goals.</p>
        </div>
        
        <div class="step-container">
            <h3>2️⃣ Get Your Plan</h3>
            <p>Receive customized meal plans that match your preferences and nutritional requirements.</p>
        </div>
        
        <div class="step-container">
            <h3>3️⃣ Track Progress</h3>
            <p>Log your meals and health metrics to monitor your journey toward better health.</p>
        </div>
        
        <div class="step-container">
            <h3>4️⃣ Adjust & Improve</h3>
            <p>Refine your plans based on what works for you with the help of our AI assistant.</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Call to Action Section with responsive design
    if st.session_state.get('_is_desktop', True):
        # Desktop view - use columns
        cta_col1, cta_col2 = st.columns([0.7, 0.3])
        
        with cta_col1:
            st.markdown("<h2>Ready to Transform Your Relationship with Food?</h2>", unsafe_allow_html=True)
            st.markdown("""
            Join a community that celebrates local chefs, from family recipes passed down through generations to brand new creations.
            Our AI-powered meal planning keeps things simple while you focus on sharing real food with real people.

            Start your journey to connected, tradition-rich meals today!
            """)
        
        with cta_col2:
            st.markdown("<br><br>", unsafe_allow_html=True)  # Spacing
            if st.button("Create Free Account", use_container_width=True, type="primary"):
                st.switch_page("views/7_register.py")
            if st.button("Explore as Guest", use_container_width=True):
                st.switch_page("views/1_assistant.py")
    else:
        # Mobile view - stack vertically
        st.markdown("<h2>Ready to Transform Your Relationship with Food?</h2>", unsafe_allow_html=True)
        st.markdown("""
        Join a community that celebrates local chefs, from family recipes passed down through generations to brand new creations.
        Our AI-powered meal planning keeps things simple while you focus on sharing real food with real people.

        Start your journey to connected, tradition-rich meals today!
        """)
        
        st.button("Create Free Account", use_container_width=True, type="primary", key="mobile_cta_1")
        st.button("Explore as Guest", use_container_width=True, key="mobile_cta_2")

except Exception as e:
    st.error("Error occurred. We're looking into it.")
    logging.error("Error occurred", exc_info=True) 

st.markdown(
    """
    <a href="https://www.buymeacoffee.com/sautai" target="_blank">
        <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px; width: 217px;" >
    </a>
    """,
    unsafe_allow_html=True
)

footer() 