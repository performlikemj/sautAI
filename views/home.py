import streamlit as st
import requests
from dotenv import load_dotenv
import os
import datetime
import logging
from utils import login_form, toggle_chef_mode, validate_input, footer, fetch_and_update_user_profile, navigate_to_page

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
                            navigate_to_page('assistant')  # Navigate to assistant page after login
                        else:
                            st.error("Invalid username or password.")
                    except requests.exceptions.HTTPError as http_err:
                        st.error("Invalid username or password.")
                        logging.warning(f"Login failed: {http_err}")
                    except requests.exceptions.RequestException as req_err:
                        st.error("Unable to connect to the server. Please try again later.")
                        logging.error(f"Connection error: {req_err}")
            if register_button:
                navigate_to_page('register')

            # Password Reset Button
            if st.button("Forgot your password?"):
                navigate_to_page('account')

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
        
    # Hero Section with flexbox layout (Streamlit containers)
    try:
        # Page-level mobile responsiveness for centering on small screens
        st.markdown(
            """
            <style>
            @media (max-width: 768px) {
              .st-key-hero, .st-key-intro, .st-key-features, .st-key-steps, .st-key-cta {
                justify-content: center !important;
                align-items: center !important;
              }
              .st-key-hero h1, .st-key-hero p,
              .st-key-intro h3, .st-key-intro p,
              .st-key-steps h3, .st-key-steps p,
              .st-key-cta h2, .st-key-cta p {
                text-align: center !important;
              }
              .st-key-hero .stButton button,
              .st-key-cta .stButton button {
                width: 100% !important;
              }
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        hero = st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="center", gap="medium", key="hero")
        with hero:
            left = st.container(width="stretch")
            right = st.container(width="stretch")
        with left:
            st.markdown("""
                <h1 style="color: #5cb85c; margin-bottom: 0.25rem;">Connect With Local Chefs</h1>
                <p style="font-size: 1.15rem; line-height: 1.6; max-width: 60ch;">
                    We link you with talented cooks in your community — from chefs preserving family recipes
                    to those creating new flavors. Our AI simply helps plan your meals.
                </p>
            """, unsafe_allow_html=True)
            cta_row = st.container(horizontal=True, horizontal_alignment="left", gap="small")
            with cta_row:
                if st.button("Get Started Today 🍽️", type="primary"):
                    navigate_to_page('register')
                st.button("Explore as Guest", key="hero_guest", type="secondary", on_click=lambda: navigate_to_page('assistant'))
        with right:
            st.image("https://live.staticflickr.com/65535/54548860874_7569d1dbdc_b.jpg", use_container_width=True)
    except TypeError:
        # Fallback for older Streamlit versions without flexbox container
        hero_col1, hero_col2 = st.columns([0.6, 0.4])
        with hero_col1:
            st.markdown("""
                <h1 style=\"color: #5cb85c;\">Connect With Local Chefs</h1>
                <p style=\"font-size: 1.2rem;\">We link you with talented cooks in your community—from chefs preserving family recipes to those creating new flavors. Our AI simply helps plan your meals.</p>
            """, unsafe_allow_html=True)
            if st.button("Get Started Today 🍽️", use_container_width=True):
                navigate_to_page('register')
        with hero_col2:
            st.image("https://live.staticflickr.com/65535/54548860874_7569d1dbdc_b.jpg", use_container_width=True)
    
    st.markdown("---")  # Divider for visual separation
    
    # Introduction Section as responsive cards
    st.markdown("<h2 style='text-align: center;'>Why sautAI?</h2>", unsafe_allow_html=True)
    try:
        intro = st.container(horizontal=True, horizontal_alignment="left", gap="medium", key="intro")
        with intro:
            for title, body in [
                ("🥘 Local Connection", "Discover chefs in your neighborhood who prepare traditional favorites and exciting new meals while keeping culinary traditions alive."),
                ("🧠 AI Meal Planning", "Let our AI suggest balanced meal plans so you can focus on enjoying food and community."),
                ("🥦 Health Tracking", "Monitor your progress, track calories, and watch your health metrics improve with every meal."),
            ]:
                card = st.container(border=True, width="stretch")
                with card:
                    st.markdown(f"### {title}")
                    st.markdown(body)
    except TypeError:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("### 🥘 Local Connection")
            st.markdown("Discover chefs in your neighborhood who prepare traditional favorites and exciting new meals while keeping culinary traditions alive.")
        with c2:
            st.markdown("### 🧠 AI Meal Planning")
            st.markdown("Let our AI suggest balanced meal plans so you can focus on enjoying food and community.")
        with c3:
            st.markdown("### 🥦 Health Tracking")
            st.markdown("Monitor your progress, track calories, and watch your health metrics improve with every meal.")
    
    st.markdown("---")
    
    # Features Section with flex image + text pairs
    st.markdown("<h2 style='text-align: center;'>How sautAI Works For You</h2>", unsafe_allow_html=True)
    features_wrap = st.container(key="features")
    def feature_row(image_url: str, title: str, bullets: list[str]):
        try:
            row = st.container(horizontal=True, horizontal_alignment="left", vertical_alignment="center", gap="large")
            with row:
                img = st.container(width="stretch")
                text = st.container(width="stretch", border=True)
            with img:
                st.image(image_url, use_container_width=True)
            with text:
                st.markdown(f"### {title}")
                for b in bullets:
                    st.markdown(f"- {b}")
        except TypeError:
            c1, c2 = st.columns([0.4, 0.6])
            with c1:
                st.image(image_url, use_container_width=True)
            with c2:
                st.markdown(f"### {title}")
                for b in bullets:
                    st.markdown(f"- {b}")

    with features_wrap:
        feature_row(
        "https://live.staticflickr.com/65535/54550764768_d565973881_b.jpg",
        "Effortless Meal Planning",
        [
            "**Customized Weekly Plans** – Meals tailored to your diet and preferences",
            "**Ingredient Awareness** – Avoid allergens and disliked foods automatically",
            "**One‑Click Adjustments** – Swap meals in seconds",
            "**Chef Connections** – Connect with local chefs for preparation",
        ],
    )
        feature_row(
        "https://live.staticflickr.com/65535/54550711849_2ac8954256_b.jpg",
        "Simple Health Monitoring",
        [
            "**Calorie & Nutrition Tracking** – Log and monitor daily intake",
            "**Progress Visualization** – Clear, intuitive charts",
            "**Mood & Energy Monitoring** – See how foods affect you",
            "**Goal Setting** – Set targets and reach them",
        ],
    )
        feature_row(
        "https://live.staticflickr.com/65535/54549653432_73f6b0bdfd_b.jpg",
        "Ongoing Support",
        [
            "**AI Nutrition Assistant** – Answers to all your nutrition questions",
            "**Personalized Recommendations** – Suggestions that improve over time",
            "**Emergency Supply Planning** – Healthy options for the unexpected",
            "**Community Connection** – Learn from others on similar journeys",
        ],
    )
    
    st.markdown("---")
    
    # How It Works Section using responsive flex cards
    st.markdown("<h2 style='text-align: center;'>Simple Steps to Better Health</h2>", unsafe_allow_html=True)
    try:
        steps = st.container(horizontal=True, horizontal_alignment="left", gap="medium", key="steps")
        with steps:
            for title, desc in [
                ("1️⃣ Sign Up", "Create your profile and tell us about your dietary needs and health goals."),
                ("2️⃣ Get Your Plan", "Receive customized meal plans that match your preferences and nutritional requirements."),
                ("3️⃣ Track Progress", "Log your meals and health metrics to monitor your journey toward better health."),
                ("4️⃣ Adjust & Improve", "Refine your plans based on what works for you with the help of our AI assistant."),
            ]:
                tile = st.container(border=True, width="stretch")
                with tile:
                    st.markdown(f"### {title}")
                    st.markdown(desc)
    except TypeError:
        c1, c2, c3, c4 = st.columns(4)
        for col, (title, desc) in zip([c1, c2, c3, c4], [
            ("1️⃣ Sign Up", "Create your profile and tell us about your dietary needs and health goals."),
            ("2️⃣ Get Your Plan", "Receive customized meal plans that match your preferences and nutritional requirements."),
            ("3️⃣ Track Progress", "Log your meals and health metrics to monitor your journey toward better health."),
            ("4️⃣ Adjust & Improve", "Refine your plans based on what works for you with the help of our AI assistant."),
        ]):
            with col:
                st.markdown(f"### {title}")
                st.markdown(desc)
    
    st.markdown("---")
    
    # Call to Action Section with flex
    st.markdown("<h2>Ready to Transform Your Relationship with Food?</h2>", unsafe_allow_html=True)
    try:
        cta = st.container(horizontal=True, horizontal_alignment="left", gap="medium", key="cta")
        with cta:
            text = st.container(width="stretch", border=True)
            actions = st.container(width="stretch")
        with text:
            st.markdown("""
            Join a community that celebrates local chefs, from family recipes passed down through generations to brand new creations.
            Our AI-powered meal planning keeps things simple while you focus on sharing real food with real people.

            Start your journey to connected, tradition-rich meals today!
            """)
        with actions:
            if st.button("Create Free Account", type="primary", use_container_width=True):
                navigate_to_page('register')
            if st.button("Explore as Guest", use_container_width=True):
                navigate_to_page('assistant')
    except TypeError:
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