import pytz
import streamlit as st
import requests
import os
import datetime
import logging
from utils import api_call_with_refresh, is_user_authenticated, login_form, toggle_chef_mode, fetch_and_update_user_profile, validate_input, resend_activation_link

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("error.log"),
    logging.StreamHandler()
])

# Fetch and display user goals
def fetch_and_display_goals():
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
    response = api_call_with_refresh(f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/user_goal/', method='get', headers=headers)
    if response.status_code == 200:
        goal_data = response.json()
        return goal_data if goal_data and goal_data.get('goal_name') and goal_data.get('goal_description') else None
    else:
        st.error("Failed to fetch goals.")
        return None

# Update user goals
def update_goal(goal_name, goal_description):
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
    data = {'goal_name': goal_name, 'goal_description': goal_description}
    response = api_call_with_refresh(f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/goal_management/', method='post', headers=headers, data=data)
    return response.status_code // 100 == 2

def profile():
    # Login Form
    try:
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
        if is_user_authenticated() and st.session_state.get('email_confirmed', False):
            if 'current_role' in st.session_state and st.session_state['current_role'] != 'chef':
                st.title("Profile")

                # Check if user is logged in
                if 'user_info' in st.session_state and st.session_state.user_info:
                    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                    user_details = api_call_with_refresh(f'{os.getenv("DJANGO_URL")}/auth/api/user_details/', method='get', headers=headers)
                    address_details = api_call_with_refresh(f'{os.getenv("DJANGO_URL")}/auth/api/address_details/', method='get', headers=headers)
                    countries_details = api_call_with_refresh(f'{os.getenv("DJANGO_URL")}/auth/api/countries/', method='get', headers=headers)
                    if user_details.status_code == 200:
                        user_data = user_details.json()
                        st.session_state.user_id = user_data.get('id')  # Set user_id in session state
                        if not isinstance(user_data.get('custom_dietary_preferences'), list):
                            user_data['custom_dietary_preferences'] = []
                    else:
                        user_data = {}

                    if address_details and address_details.status_code == 200:
                        address_data = address_details.json()
                    else:
                        address_data = {}

                    if countries_details and countries_details.status_code == 200:
                        countries_list = countries_details.json() if countries_details.status_code == 200 else []

                        # Create a dictionary for easy access by country name
                        country_dict = {country['name']: country['code'] for country in countries_list}
                        country_names = list(country_dict.keys()) 
                    else:
                        country_names = []               
                    if is_user_authenticated():
                        # Define a container for each field
                        username_container = st.container()
                        email_container = st.container()
                        phone_container = st.container()
                        diet_container = st.container()
                        allergy_container = st.container()
                        goal_container = st.container()
                        address_container = st.container()
                        language_container = st.container()
                        timezone_container = st.container()
                        email_daily_instructions = st.container()
                        email_meal_plan_saved = st.container()
                        email_instruction_generation = st.container()            
                        # Goal management section
                        with st.form("profile_update_form"):
                            goal_data = fetch_and_display_goals()

                            username = st.text_input("Username", value=user_data.get('username', ''))
                            email = st.text_input("Email", value=user_data.get('email', ''))
                            phone_number = st.text_input("Phone Number", value=user_data.get('phone_number', ''))

                            valid_username, username_msg = validate_input(username, 'username')
                            valid_email, email_msg = validate_input(email, 'email')
                            valid_phone, phone_msg = validate_input(phone_number, 'phone_number')

                            if not valid_username:
                                st.error(username_msg)
                            elif not valid_email:
                                st.error(email_msg)
                            elif not valid_phone:
                                st.error(phone_msg)
                            else:
                                dietary_preferences = [
                                    'Everything', 'Vegetarian', 'Pescatarian', 'Gluten-Free', 'Keto', 
                                    'Paleo', 'Halal', 'Kosher', 'Low-Calorie', 'Low-Sodium', 'High-Protein', 
                                    'Dairy-Free', 'Nut-Free', 'Raw Food', 'Whole 30', 'Low-FODMAP', 
                                    'Diabetic-Friendly', 'Vegan'
                                ]

                                # Get the user's dietary preferences (this could be a list of preferences if you're using ManyToMany)
                                user_dietary_preference = user_data.get('dietary_preferences', ['Everything'])

                                # Use the default argument to select the user's current preferences
                                selected_dietary_preference = st.multiselect(
                                    "Dietary Preference", dietary_preferences, default=user_dietary_preference
                                )

                                custom_dietary_preferences_input = st.text_area(
                                    "Custom Dietary Preferences (comma separated)", 
                                    value=', '.join(user_data.get('custom_dietary_preferences', [])) if user_data.get('custom_dietary_preferences') else ''
                                )

                                allergies = [
                                    'Peanuts', 'Tree nuts', 'Milk', 'Egg', 'Wheat', 'Soy', 'Fish', 'Shellfish', 'Sesame', 'Mustard', 
                                    'Celery', 'Lupin', 'Sulfites', 'Molluscs', 'Corn', 'Gluten', 'Kiwi', 'Latex', 'Pine Nuts', 
                                    'Sunflower Seeds', 'Poppy Seeds', 'Fennel', 'Peach', 'Banana', 'Avocado', 'Chocolate', 
                                    'Coffee', 'Cinnamon', 'Garlic', 'Chickpeas', 'Lentils'
                                ]
                                custom_allergies = st.text_area("Custom Allergies (comma separated)", value=user_data.get('custom_allergies', ''))
                                default_allergies = user_data.get('allergies', [])
                                valid_default_allergies = [allergy for allergy in default_allergies if allergy in allergies]
                                selected_allergies = st.multiselect("Allergies", allergies, default=valid_default_allergies)                 
                                street = st.text_input("Street", value=address_data.get('street', ''))
                                city = st.text_input("City", value=address_data.get('city', ''))
                                state = st.text_input("State", value=address_data.get('state', ''))
                                postalcode = st.text_input("Postal Code", value=address_data.get('postalcode', ''))
                                # Fetch the country from address_data
                                user_country = address_data.get('country', '')

                                # Check if the fetched country is in the list of country names
                                if user_country in country_names:
                                    country_index = country_names.index(user_country)
                                else:
                                    country_index = 0  # Default to the first country in the list

                                # Create the selectbox with the calculated index
                                country = st.selectbox("Country", country_names, index=country_index)
                                # Time zone selection
                                timezones = pytz.all_timezones
                                selected_timezone = st.selectbox('Time Zone', options=timezones, index=timezones.index(user_data.get('timezone', 'UTC')))
                                # Define a dictionary for languages
                                language_options = {
                                    'en': 'English',
                                    'ja': 'Japanese',
                                    'es': 'Spanish',
                                    'fr': 'French',
                                }
                                language_labels = list(language_options.values())
                                language_keys = list(language_options.keys())
                                current_language = language_options.get(user_data.get('preferred_language', 'en'))
                                preferred_language = st.selectbox("Preferred Language", language_labels, index=language_labels.index(current_language))
                                email_daily_instructions = st.radio(
                                    "Receive daily emails with that day's cooking instructions?",
                                    ('Yes', 'No'),
                                    index=0 if user_data.get('email_daily_instructions', True) else 1
                                )

                                email_meal_plan_saved = st.radio(
                                    "Receive a shopping list when your meal plan is saved or updated?",
                                    ('Yes', 'No'),
                                    index=0 if user_data.get('email_meal_plan_saved', True) else 1
                                )

                                email_instruction_generation = st.radio(
                                    "Receive an email when you request cooking instructions?",
                                    ('Yes', 'No'),
                                    index=0 if user_data.get('email_instruction_generation', True) else 1
                                )                   
                                # Get the corresponding key for the selected value
                                selected_language_code = language_keys[language_labels.index(preferred_language)]

                                st.subheader("User Goals")
                                if goal_data:
                                    st.write(f"**{goal_data['goal_name']}**: {goal_data['goal_description']}")
                                else:
                                    st.info("No goals set yet. Use the form below to add your goals.")
                                goal_name = st.text_input("Goal Name", value=goal_data['goal_name'] if goal_data else "")
                                goal_description = st.text_area("Goal Description", value=goal_data['goal_description'] if goal_data else "")
                            
                                submitted = st.form_submit_button("Update Profile")

                                if submitted:
                                    custom_dietary_preferences = [
                                        pref.strip() for pref in custom_dietary_preferences_input.split(',') if pref.strip()
                                    ]
                                    profile_data = {
                                        # User fields
                                        'username': username,
                                        'email': email,
                                        'phone_number': phone_number,
                                        'dietary_preferences': selected_dietary_preference,
                                        'custom_dietary_preferences': custom_dietary_preferences,
                                        'allergies': selected_allergies,
                                        'custom_allergies': custom_allergies,
                                        'timezone': selected_timezone,
                                        'preferred_language': selected_language_code,
                                        'email_daily_instructions': email_daily_instructions == 'Yes',
                                        'email_meal_plan_saved': email_meal_plan_saved == 'Yes',
                                        'email_instruction_generation': email_instruction_generation == 'Yes',
                                        # Address data
                                        'address': {
                                            'street': street,
                                            'city': city,
                                            'state': state,
                                            'postalcode': postalcode,
                                            'country': country
                                        }
                                    }
                                    update_response = api_call_with_refresh(
                                        url=f'{os.getenv("DJANGO_URL")}/auth/api/update_profile/',
                                        method='post',
                                        data=profile_data,
                                        headers={'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                                    )
                                    if update_response.status_code == 200:
                                        st.success("Profile updated successfully!")
                                        if goal_name and goal_description:
                                            if update_goal(goal_name, goal_description):
                                                st.success("Goal updated successfully!")
                                            else:
                                                st.error("Failed to update goal.")
                                        fetch_and_update_user_profile()
                                    else:
                                        st.error(f"Failed to update profile: {update_response.text}")

                # Account Deletion Section
                st.subheader("Delete Account")
                st.warning("**This action cannot be undone.** All your data will be permanently deleted.")

                # Confirmation inputs
                confirmation_input = st.text_input('Type "done eating" to confirm account deletion.')
                password_input = st.text_input("Enter your password", type="password")

                if st.button("Delete My Account"):
                    if confirmation_input == 'done eating':
                        if password_input:
                            # Make API call to delete account
                            headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                            response = api_call_with_refresh(
                                url=f'{os.getenv("DJANGO_URL")}/auth/api/delete_account/',
                                headers=headers,
                                method='delete',
                                data={'confirmation': confirmation_input, 'password': password_input}
                            )
                            if response.status_code == 200:
                                st.success("Your account has been deleted successfully.")
                                # Clear session state and redirect or refresh the page
                                for key in list(st.session_state.keys()):
                                    del st.session_state[key]
                                st.rerun()
                            else:
                                error_message = response.json().get('message', 'Unknown error')
                                st.error(f"Failed to delete account: {error_message}")
                        else:
                            st.error('Please enter your password to confirm account deletion.')
                    else:
                        st.error('You must type "done eating" exactly to confirm account deletion.')
                else:
                    # User is not logged in, display a message or redirect
                    st.warning("Please log in to view and update your profile.")

        # If the email is not confirmed, restrict access and prompt to resend activation link
        elif is_user_authenticated() and not st.session_state.get('email_confirmed', False):
            st.warning("Your email address is not confirmed. Please confirm your email to access all features.")
            if st.button("Resend Activation Link"):
                resend_activation_link(st.session_state['user_id'])

            # Account Deletion Section
            st.subheader("Delete Account")
            st.warning("**This action cannot be undone.** All your data will be permanently deleted.")

            # Confirmation inputs
            confirmation_input = st.text_input('Type "done eating" to confirm account deletion.')
            password_input = st.text_input("Enter your password", type="password")

            if st.button("Delete My Account"):
                if confirmation_input == 'done eating':
                    if password_input:
                        # Make API call to delete account
                        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                        response = api_call_with_refresh(
                            url=f'{os.getenv("DJANGO_URL")}/auth/api/delete_account/',
                            headers=headers,
                            method='delete',
                            data={'confirmation': confirmation_input, 'password': password_input}
                        )
                        if response.status_code == 200:
                            st.success("Your account has been deleted successfully.")
                            # Clear session state and redirect or refresh the page
                            for key in list(st.session_state.keys()):
                                del st.session_state[key]
                            st.rerun()
                        else:
                            error_message = response.json().get('message', 'Unknown error')
                            st.error(f"Failed to delete account: {error_message}")
                    else:
                        st.error('Please enter your password to confirm account deletion.')
                else:
                    st.error('You must type "done eating" exactly to confirm account deletion.')

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        st.error("An unexpected error occurred. Please try again later.")

if __name__ == "__main__":
    profile()
