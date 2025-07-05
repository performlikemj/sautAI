import streamlit as st
import os
from dotenv import load_dotenv
import openai
import json
import re
import time
import requests
import pycountry
import datetime
import pytz
from utils import (
    api_call_with_refresh,
    login_form,
    toggle_chef_mode,
    fetch_and_update_user_profile,
    validate_input,
    parse_comma_separated_input,
    footer,
    fetch_languages,
    navigate_to_page,
    start_onboarding_conversation,
    display_onboarding_stream,
)
from security_utils import (
    sanitize_registration_data, 
    validate_registration_security,
    InputSanitizer, 
    SecurityValidator,
    RateLimiter,
    CSRFProtection
)
import logging
import traceback

# Configure logging
logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='history.log', # Log to a file. Remove this to log to console
                    filemode='w') # 'w' to overwrite the log file on each run, 'a' to append

# Initialize rate limiter (in production, use Redis or database-backed limiter)
rate_limiter = RateLimiter(max_attempts=5, window_minutes=15)

st.title("Register")

if 'registration_method' not in st.session_state:
    st.session_state.registration_method = 'chat'

if 'onboarding_chat_history' not in st.session_state:
    st.session_state.onboarding_chat_history = []
if 'onboarding_guest_id' not in st.session_state:
    st.session_state.onboarding_guest_id = None
if 'onboarding_response_id' not in st.session_state:
    st.session_state.onboarding_response_id = None
if 'onboarding_complete' not in st.session_state:
    st.session_state.onboarding_complete = False

method_choice = st.radio(
    "How would you like to register?",
    ("Chat with assistant", "Traditional form"),
    index=0 if st.session_state.registration_method == 'chat' else 1,
)

st.session_state.registration_method = (
    'chat' if method_choice == "Chat with assistant" else 'form'
)

# ----------------------------
# Chat-based Registration
# ----------------------------

if st.session_state.registration_method == 'chat':
    if 'onboarding_guest_id' not in st.session_state:
        guest = start_onboarding_conversation()
        if guest:
            st.session_state.onboarding_guest_id = guest
            st.session_state.onboarding_chat_history = []
            st.session_state.onboarding_response_id = None

    if not st.session_state.get('onboarding_complete'):
        st.write("Create an account by chatting with our onboarding assistant.")

        chat_container = st.container()
        for msg in st.session_state.get('onboarding_chat_history', []):
            with chat_container.chat_message(msg['role']):
                st.markdown(msg['content'])

        user_msg = st.chat_input("Message")
        if user_msg:
            st.session_state.onboarding_chat_history.append({'role': 'user', 'content': user_msg})
            with chat_container.chat_message('user'):
                st.markdown(user_msg)
            with chat_container.chat_message('assistant'):
                resp_id, full_text, tool_out = display_onboarding_stream(
                    user_msg,
                    st.session_state.onboarding_guest_id,
                    st.session_state.get('onboarding_response_id')
                )
                st.session_state.onboarding_response_id = resp_id
                st.session_state.onboarding_chat_history.append({'role': 'assistant', 'content': full_text})
                if tool_out:
                    try:
                        data = json.loads(tool_out) if isinstance(tool_out, str) else tool_out
                        st.session_state['user_info'] = data
                        st.session_state['user_id'] = data.get('user_id')
                        st.session_state['access_token'] = data.get('access')
                        st.session_state['refresh_token'] = data.get('refresh')
                        st.session_state['is_logged_in'] = True
                        st.session_state['onboarding_complete'] = True
                        st.rerun()
                    except Exception as e:
                        logging.error(f"Failed to process tool output: {e}")
        st.stop()

# Content moved from register() to top level
try:
    if st.session_state.get('onboarding_complete'):
        st.success("Account created! You can adjust your details below.")
    st.write("Create an account.")

    with st.form(key='registration_form'):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        phone_number = st.text_input("Phone Number")
        dietary_preferences = [ 'Everything', 'Vegetarian', 'Pescatarian', 'Gluten-Free', 'Keto', 'Paleo', 'Halal', 'Kosher', 'Low-Calorie', 'Low-Sodium', 'High-Protein', 'Dairy-Free', 'Nut-Free', 'Raw Food', 'Whole 30', 'Low-FODMAP', 'Diabetic-Friendly', 'Vegan']
        selected_dietary_preferences = st.multiselect("Dietary Preferences", dietary_preferences, default=[])
        custom_dietary_preferences_input = st.text_area(
            "Custom Dietary Preferences (comma separated)", 
            value='',
            help="Enter multiple custom dietary preferences separated by commas. Example: Carnivore, Lacto-Vegan, Flexitarian"
        )            
        allergies = [
            'Peanuts', 'Tree nuts', 'Milk', 'Egg', 'Wheat', 'Soy', 'Fish', 'Shellfish', 'Sesame', 'Mustard', 
            'Celery', 'Lupin', 'Sulfites', 'Molluscs', 'Corn', 'Gluten', 'Kiwi', 'Latex', 'Pine Nuts', 
            'Sunflower Seeds', 'Poppy Seeds', 'Fennel', 'Peach', 'Banana', 'Avocado', 'Chocolate', 
            'Coffee', 'Cinnamon', 'Garlic', 'Chickpeas', 'Lentils'
        ]
        selected_allergies = st.multiselect("Allergies", allergies, default=[]) 
        custom_allergies = st.text_area("Custom Allergies (comma separated)", "", help="Enter multiple custom allergies separated by commas. Example: Peanuts, Shellfish, Kiwi")
        custom_allergies_list = [a.strip() for a in custom_allergies.split(',') if a.strip()]
        household_member_count = st.number_input(
            "Household Members",
            min_value=1,
            value=1,
            help="How many people are in your household?"
        )

        # Create household member input fields
        # Values will be automatically stored in session state with the keys
        for i in range(int(household_member_count)):
            with st.expander(f"Household Member {i+1} (optional)"):
                st.text_input("Name", key=f"register_member_name_{i}")
                st.number_input("Age", min_value=0, value=0, step=1, key=f"register_member_age_{i}")
                st.multiselect("Dietary Preferences", dietary_preferences, default=[], key=f"register_member_diet_{i}")
                st.text_area("Notes", key=f"register_member_notes_{i}")
        
        # Debug: Show current form values before submission (only if more than 1 household member)
        if household_member_count > 1:
            with st.expander("🔍 Debug: Current Household Members Data", expanded=False):
                st.write("**Household Members Form Data:**")
                for i in range(int(household_member_count)):
                    name = st.session_state.get(f"register_member_name_{i}", '')
                    age = st.session_state.get(f"register_member_age_{i}", 0)
                    dietary_prefs = st.session_state.get(f"register_member_diet_{i}", [])
                    notes = st.session_state.get(f"register_member_notes_{i}", '')
                    
                    if name or age or dietary_prefs or notes:
                        st.json({
                            f"Member {i+1}": {
                                "name": name,
                                "age": age,
                                "dietary_preferences": dietary_prefs,
                                "notes": notes
                            }
                        })
                st.caption("This shows what household member data will be submitted when you register")
        emergency_supply_goal = st.number_input("Emergency Supply Goal (days)", min_value=0, value=0,
            help="How many days of emergency supplies do you want to keep in your pantry?")
        
        # Address fields
        st.subheader("Address")
        st.write("""
        Your address is used to:
        1. Find supported supermarkets in your area
        2. Find chefs in your area to provide meal planning meals
        
        **Note:** If you provide a country, you must also provide a postal code (and vice versa). 
        Street and city are recommended when providing location information.
        """)
        street = st.text_input("Street", help="Your street address (recommended when providing location)")
        city = st.text_input("City", help="Your city (recommended when providing location)")
        state = st.text_input("State/Province", help="Your state or province")
        postal_code = st.text_input("Postal Code", help="Required if you select a country")
        # Get a list of all countries
        countries = [country.name for country in pycountry.countries]
        selected_country = st.selectbox("Country", countries, help="Required if you provide a postal code")
        # Convert the selected country to its two-letter country code
        country_code = pycountry.countries.get(name=selected_country).alpha_2

        # Fetch available languages from API
        languages = fetch_languages()
        
        # Create language display options - show both language name and native name
        language_display_options = [f"{lang['name']} ({lang['name_local']})" for lang in languages]
        language_codes = [lang['code'] for lang in languages]
        
        # Set default to English
        default_language_index = language_codes.index('en') if 'en' in language_codes else 0
        
        # Language selection with search/filter ability
        st.subheader("Language Preference")
        preferred_language = st.selectbox(
            "Preferred Language", 
            language_display_options, 
            index=default_language_index,
            help="Select your preferred language for the application"
        )
        
        # Get the corresponding language code for the selected display option
        selected_language_code = language_codes[language_display_options.index(preferred_language)]
                
        # Time zone selection
        timezones = pytz.all_timezones
        selected_timezone = st.selectbox('Time Zone', options=timezones, index=timezones.index('UTC'))

        # Goal fields
        goal_name = st.text_input("Goal Name")
        goal_description = st.text_area("Goal Description")

        submit_button = st.form_submit_button(label='Register')
        if submit_button:
            # Get client IP for rate limiting (in production, use real IP detection)
            client_ip = st.session_state.get('client_ip', 'unknown')
            
            # Check rate limiting
            if rate_limiter.is_rate_limited(client_ip):
                st.error("Too many registration attempts. Please try again later.")
                st.stop()
            
            # Basic validation using existing validators
            valid_username, username_msg = validate_input(username, 'username')
            valid_email, email_msg = validate_input(email, 'email')
            valid_password, password_msg = validate_input(password, 'password')
            valid_phone, phone_msg = validate_input(phone_number, 'phone_number')
            valid_postal, postal_msg = validate_input(postal_code, 'postal_code')

            # Create a list of all validation errors
            validation_errors = []
            if not valid_username:
                validation_errors.append(f"Username Error: {username_msg}")
            if not valid_email:
                validation_errors.append(f"Email Error: {email_msg}")
            if not valid_password:
                validation_errors.append(f"Password Error: {password_msg}")
            if not valid_phone and phone_number:  # Only validate phone if provided
                validation_errors.append(f"Phone Number Error: {phone_msg}")
            if not valid_postal and postal_code:  # Only validate postal if provided
                validation_errors.append(f"Postal Code Error: {postal_msg}")
            
            # Validate that both country and postal code are provided together
            if (selected_country and not postal_code.strip()) or (postal_code.strip() and not selected_country):
                validation_errors.append("Address Error: Both country and postal code must be provided together.")
            
            # If either country or postal code is provided, both street and city should also be provided
            if (selected_country or postal_code.strip()) and (not street.strip() or not city.strip()):
                validation_errors.append("Address Error: When providing country and postal code, street and city are also required.")

            # Parse custom dietary preferences
            custom_dietary_preferences = parse_comma_separated_input(custom_dietary_preferences_input)

            # Process household members data using session state
            household_members = []
            for i in range(int(household_member_count)):
                # Access values from session state using the widget keys
                name = st.session_state.get(f"register_member_name_{i}", '')
                age = st.session_state.get(f"register_member_age_{i}", 0)
                dietary_prefs = st.session_state.get(f"register_member_diet_{i}", [])
                notes = st.session_state.get(f"register_member_notes_{i}", '')
                
                # Clean up the data - ensure proper types and handle empty values
                member_data = {
                    'name': str(name).strip() if name else '',
                    'age': int(age) if age and age > 0 else None,
                    'dietary_preferences': list(dietary_prefs) if dietary_prefs else [],
                    'notes': str(notes).strip() if notes else '',
                }
                household_members.append(member_data)
                logging.warning(f"Registration - Member {i+1} data: {member_data}")
            
            # Filter out completely empty members (no name, age, prefs, or notes)
            filtered_members = []
            for member in household_members:
                if (member['name'] or member['age'] or member['dietary_preferences'] or member['notes']):
                    filtered_members.append(member)
            
            household_members = filtered_members
            logging.warning(f"Registration - Final household members after filtering: {household_members}")

            # Create user data structure
            user_data = {
                "user": {
                    "username": username,
                    "email": email,
                    "password": password,
                    "phone_number": phone_number,
                    "dietary_preferences": selected_dietary_preferences,
                    "custom_dietary_preferences": custom_dietary_preferences,
                    "allergies": selected_allergies,
                    "custom_allergies": custom_allergies_list,
                    "timezone": selected_timezone,
                    "preferred_language": selected_language_code,
                    "household_member_count": household_member_count,
                    "household_members": household_members,
                    "emergency_supply_goal": emergency_supply_goal
                },
                "address": {
                    "street": street,
                    "city": city,
                    "state": state,
                    "country": country_code,
                    "postalcode": postal_code
                },
                "goal": {
                    "goal_name": goal_name,
                    "goal_description": goal_description
                }
            }
            
            # Security validation and sanitization
            security_valid, security_errors = validate_registration_security(user_data)
            if not security_valid:
                validation_errors.extend(security_errors)
            
            # Advanced security validation using new validators
            username_secure, username_sec_msg = SecurityValidator.validate_username_format(username)
            if not username_secure:
                validation_errors.append(f"Username Security: {username_sec_msg}")
                
            email_secure, email_sec_msg = SecurityValidator.validate_email_format(email)
            if not email_secure:
                validation_errors.append(f"Email Security: {email_sec_msg}")
                
            password_secure, password_sec_msg = SecurityValidator.validate_password_strength(password)
            if not password_secure:
                validation_errors.append(f"Password Security: {password_sec_msg}")

            # Display all validation errors in a formatted way
            if validation_errors:
                st.error("Please fix the following errors:")
                for error in validation_errors:
                    st.warning(error)
                st.stop()
            
            # Sanitize user data before sending to API
            sanitized_data = sanitize_registration_data(user_data)
            
            # Log sanitization for security monitoring and debug household members
            logging.warning(f"Registration attempt for username: {InputSanitizer.sanitize_username(username)[:10]}...")
            logging.warning(f"Registration - Household member count: {household_member_count}")
            logging.warning(f"Registration - Available session state keys: {[k for k in st.session_state.keys() if 'register_member' in k]}")
            logging.warning(f"Registration - Submitting household members data: {household_members}")
            logging.warning(f"Registration - Full user data structure: {user_data}")

            try:
                with st.spinner("Registering your account..."):
                    api_url = f"{os.getenv('DJANGO_URL')}/auth/api/register/"
                    response = requests.post(api_url, json=sanitized_data, timeout=10)
                
                if response.status_code == 200:
                    st.success("Registration successful!")
                    
                    # Show household members confirmation if any were submitted
                    if household_members:
                        st.success(f"✅ {len(household_members)} household member(s) registered:")
                        for i, member in enumerate(household_members):
                            if member.get('name'):
                                st.caption(f"Member {i+1}: {member['name']} (Age: {member.get('age', 'Not specified')})")
                    
                    st.info("Please check your email to activate your account.")
                    # Navigate to home page
                    navigate_to_page('home')
                elif response.status_code == 400:
                    # Handle bad request - validation errors
                    try:
                        error_data = response.json()
                        errors = error_data.get('errors', {})
                        
                        # Log detailed errors for debugging but show sanitized messages to users
                        logging.warning(f"Registration validation errors: {errors}")
                        
                        if isinstance(errors, dict):
                            # Only display safe, user-friendly error messages
                            user_friendly_errors = []
                            
                            for field, messages in errors.items():
                                if field == '__all__':
                                    # Handle general form validation errors
                                    if isinstance(messages, list):
                                        for msg in messages:
                                            if 'country and postal code must be provided together' in str(msg).lower():
                                                user_friendly_errors.append("Please ensure both country and postal code are provided together.")
                                            elif 'duplicate' in str(msg).lower() or 'already exists' in str(msg).lower():
                                                # Don't reveal specific account information - generic message
                                                user_friendly_errors.append("Registration failed. Please check your information and try again.")
                                            else:
                                                # Generic message for other validation errors
                                                user_friendly_errors.append("Please check your information and try again.")
                                    else:
                                        msg = str(messages)
                                        if 'country and postal code must be provided together' in msg.lower():
                                            user_friendly_errors.append("Please ensure both country and postal code are provided together.")
                                        elif 'duplicate' in msg.lower() or 'already exists' in msg.lower():
                                            # Don't reveal specific account information - generic message
                                            user_friendly_errors.append("Registration failed. Please check your information and try again.")
                                        else:
                                            user_friendly_errors.append("Please check your information and try again.")
                                            
                                elif field in ['username', 'email', 'password']:
                                    # Only show sanitized messages for sensitive fields
                                    if isinstance(messages, list):
                                        for msg in messages:
                                            if 'already exists' in str(msg).lower() or 'duplicate' in str(msg).lower():
                                                if field == 'username':
                                                    user_friendly_errors.append("This username is already taken. Please choose a different one.")
                                                elif field == 'email':
                                                    # Don't reveal email existence - prevent enumeration
                                                    user_friendly_errors.append("Registration failed. Please check your information and try again.")
                                            elif 'invalid' in str(msg).lower():
                                                if field == 'email':
                                                    user_friendly_errors.append("Please enter a valid email address.")
                                                elif field == 'password':
                                                    user_friendly_errors.append("Please choose a stronger password.")
                                            else:
                                                # Generic message for other field errors
                                                user_friendly_errors.append(f"Please check your {field} and try again.")
                                    else:
                                        msg = str(messages)
                                        if 'already exists' in msg.lower() or 'duplicate' in msg.lower():
                                            if field == 'username':
                                                user_friendly_errors.append("This username is already taken. Please choose a different one.")
                                            elif field == 'email':
                                                # Don't reveal email existence - prevent enumeration
                                                user_friendly_errors.append("Registration failed. Please check your information and try again.")
                                        elif 'invalid' in msg.lower():
                                            if field == 'email':
                                                user_friendly_errors.append("Please enter a valid email address.")
                                            elif field == 'password':
                                                user_friendly_errors.append("Please choose a stronger password.")
                                        else:
                                            user_friendly_errors.append(f"Please check your {field} and try again.")
                            
                            if user_friendly_errors:
                                st.error("Registration failed. Please fix the following issues:")
                                for msg in user_friendly_errors:
                                    st.warning(msg)
                                
                                # Show generic login link instead of conditional one
                                st.info("Already have an account? [Click here to log in](pages/home.py)")
                            else:
                                # Fallback generic message
                                st.error("Registration failed. Please check your information and try again.")
                        else:
                            # Generic message for unexpected error structure
                            st.error("Registration failed. Please check your information and try again.")
                            
                    except (ValueError, KeyError) as e:
                        # Log the parsing error but don't expose it to user
                        logging.error(f"Error parsing registration response: {e}")
                        st.error("Registration failed. Please check your information and try again.")
                        
                elif response.status_code == 500:
                    # Handle internal server error - don't expose server details
                    logging.error(f"Server error during registration: {response.status_code}")
                    st.error("We're experiencing technical difficulties. Please try again in a few moments.")
                    st.info("If the problem continues, please contact support.")
                    
                else:
                    # Handle other status codes - don't expose specific codes to user
                    logging.error(f"Unexpected registration response: {response.status_code}")
                    st.error("Registration failed. Please try again.")
                    
            except requests.exceptions.RequestException as e:
                st.error("Failed to register due to a network issue. Please try again later.")
                logging.error(f"Registration network error: {e}")
            except Exception as e:
                st.error("An unexpected error occurred during registration.")
                logging.error(f"Unexpected error during registration: {e}")

        st.markdown(
            """
            <a href="https://www.buymeacoffee.com/sautai" target="_blank">
                <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px; width: 217px;" >
            </a>
            """,
            unsafe_allow_html=True
        )

        footer()
except Exception as e:
    logging.error(f"An error occurred: {str(e)}")
    st.error("An unexpected error occurred. Please try again later.")
