import pytz
import streamlit as st
import requests
import os
import datetime
import logging
from utils import api_call_with_refresh, is_user_authenticated, login_form, toggle_chef_mode, fetch_and_update_user_profile, validate_input, resend_activation_link, footer

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("error.log"),
    logging.StreamHandler()
])

def fetch_and_display_goals():
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
    response = api_call_with_refresh(f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/user_goal/', method='get', headers=headers)
    if response.status_code == 200:
        goal_data = response.json()
        return goal_data if goal_data and goal_data.get('goal_name') and goal_data.get('goal_description') else None
    else:
        st.error("Failed to fetch goals.")
        return None

def update_goal(goal_name, goal_description):
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
    data = {'goal_name': goal_name, 'goal_description': goal_description}
    response = api_call_with_refresh(f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/goal_management/', method='post', headers=headers, data=data)
    return response.status_code // 100 == 2

# Main content - moved from profile() to top level
try:
    # If not logged in, show login form
    if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
        login_form()
        st.stop()

    # If logged in, show logout button
    if st.button("Logout", key='form_logout'):
        # Clear session state but preserve navigation
        navigation_state = st.session_state.get("navigation", None)
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        if navigation_state:
            st.session_state["navigation"] = navigation_state
        st.success("Logged out successfully!")
        st.rerun()

    # Toggle chef mode
    toggle_chef_mode()

    # Check email confirmation
    if is_user_authenticated() and not st.session_state.get('email_confirmed', False):
        st.warning("Your email address is not confirmed. Please confirm your email to access all features.")
        if st.button("Resend Activation Link"):
            resend_activation_link(st.session_state['user_id'])

        # Account deletion option
        st.subheader("Delete Account")
        st.warning("**This action cannot be undone.**")
        confirmation_input = st.text_input('Type "done eating" to confirm account deletion.')
        password_input = st.text_input("Enter your password", type="password")

        if st.button("Delete My Account"):
            if confirmation_input == 'done eating' and password_input:
                headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                response = api_call_with_refresh(
                    url=f'{os.getenv("DJANGO_URL")}/auth/api/delete_account/',
                    headers=headers,
                    method='delete',
                    data={'confirmation': confirmation_input, 'password': password_input}
                )
                if response.status_code == 200:
                    st.success("Your account has been deleted successfully.")
                    # Clear session state but preserve navigation
                    navigation_state = st.session_state.get("navigation", None)
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    if navigation_state:
                        st.session_state["navigation"] = navigation_state
                    st.rerun()
                else:
                    error_msg = response.json().get('message', 'Unknown error')
                    st.error(f"Failed to delete account: {error_msg}")
            else:
                st.error('You must type "done eating" exactly and provide your password.')
        st.stop()  # Stop execution instead of using return

    # If user is authenticated and email is confirmed
    elif is_user_authenticated() and st.session_state.get('email_confirmed', False):
        if 'current_role' in st.session_state and st.session_state['current_role'] != 'chef':
            st.title("Profile")

            # Fetch user details
            headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
            user_details = api_call_with_refresh(f'{os.getenv("DJANGO_URL")}/auth/api/user_details/', method='get', headers=headers)
            address_details = api_call_with_refresh(f'{os.getenv("DJANGO_URL")}/auth/api/address_details/', method='get', headers=headers)
            countries_details = api_call_with_refresh(f'{os.getenv("DJANGO_URL")}/auth/api/countries/', method='get', headers=headers)

            if user_details.status_code == 200:
                user_data = user_details.json()
                st.session_state.user_id = user_data.get('id')
                if not isinstance(user_data.get('custom_dietary_preferences'), list):
                    user_data['custom_dietary_preferences'] = []
            else:
                user_data = {}

            address_data = address_details.json() if address_details and address_details.status_code == 200 else {}

            countries_list = countries_details.json() if countries_details and countries_details.status_code == 200 else []
            country_dict = {country['name']: country['code'] for country in countries_list}
            country_names = list(country_dict.keys())

            # Default values for fields
            username_val = user_data.get('username', '')
            email_val = user_data.get('email', '')
            phone_val = user_data.get('phone_number', '')
            timezone_val = user_data.get('timezone', 'UTC')
            preferred_language_val = user_data.get('preferred_language', 'en')
            dietary_prefs_val = user_data.get('dietary_preferences', ['Everything'])
            custom_prefs_val = ', '.join(user_data.get('custom_dietary_preferences', []))
            allergies_val = user_data.get('allergies', [])
            custom_allergies_val = ', '.join(user_data.get('custom_allergies', []))
            email_daily_inst_val = user_data.get('email_daily_instructions', True)
            email_meal_plan_saved_val = user_data.get('email_meal_plan_saved', True)
            email_instr_gen_val = user_data.get('email_instruction_generation', True)
            preferred_servings_val = user_data.get('preferred_servings', 1)
            emergency_supply_goal_val = user_data.get('emergency_supply_goal', st.session_state.get('emergency_supply_goal', 0))

            street_val = address_data.get('street', '')
            city_val = address_data.get('city', '')
            state_val = address_data.get('state', '')
            postal_val = address_data.get('postalcode', '')
            user_country = address_data.get('country', '')
            country_index = country_names.index(user_country) if user_country in country_names else 0

            dietary_preferences = [
                'Everything', 'Vegetarian', 'Pescatarian', 'Gluten-Free', 'Keto', 
                'Paleo', 'Halal', 'Kosher', 'Low-Calorie', 'Low-Sodium', 'High-Protein', 
                'Dairy-Free', 'Nut-Free', 'Raw Food', 'Whole 30', 'Low-FODMAP', 
                'Diabetic-Friendly', 'Vegan'
            ]

            all_allergies = [
                'Peanuts', 'Tree nuts', 'Milk', 'Egg', 'Wheat', 'Soy', 'Fish', 'Shellfish', 'Sesame', 'Mustard', 
                'Celery', 'Lupin', 'Sulfites', 'Molluscs', 'Corn', 'Gluten', 'Kiwi', 'Latex', 'Pine Nuts', 
                'Sunflower Seeds', 'Poppy Seeds', 'Fennel', 'Peach', 'Banana', 'Avocado', 'Chocolate', 
                'Coffee', 'Cinnamon', 'Garlic', 'Chickpeas', 'Lentils'
            ]

            # Languages
            language_options = {'en': 'English', 'ja': 'Japanese', 'es': 'Spanish', 'fr': 'French'}
            language_labels = list(language_options.values())
            language_keys = list(language_options.keys())
            current_language_label = language_options.get(preferred_language_val, 'English')

            # Timezone options
            timezones = pytz.all_timezones

            goal_data = fetch_and_display_goals()

            with st.form("profile_update_form"):
                st.subheader("User Information")
                username_input = st.text_input("Username", value=username_val)
                email_input = st.text_input("Email", value=email_val)
                phone_input = st.text_input("Phone Number", value=phone_val)

                # Address fields
                st.subheader("Address")
                street_input = st.text_input("Street", value=street_val)
                city_input = st.text_input("City", value=city_val)
                state_input = st.text_input("State", value=state_val)
                postal_input = st.text_input("Postal Code", value=postal_val)
                country_selected = st.selectbox("Country", country_names, index=country_index)

                # Now do the validation checks after all inputs are defined
                validation_errors = []

                if username_input:
                    valid_username, username_msg = validate_input(username_input, 'username')
                    if not valid_username:
                        validation_errors.append(f"Username Error: {username_msg}")

                if email_input:
                    valid_email, email_msg = validate_input(email_input, 'email')
                    if not valid_email:
                        validation_errors.append(f"Email Error: {email_msg}")

                if phone_input:
                    valid_phone, phone_msg = validate_input(phone_input, 'phone_number')
                    if not valid_phone:
                        validation_errors.append(f"Phone Number Error: {phone_msg}")

                if postal_input:
                    valid_postal, postal_msg = validate_input(postal_input, 'postal_code')
                    if not valid_postal:
                        validation_errors.append(f"Postal Code Error: {postal_msg}")

                # Display validation errors if any
                if validation_errors:
                    st.error("Please fix the following errors:")
                    for error in validation_errors:
                        st.warning(error)
                    # Instead of using return which is invalid at top level
                    # Exit the form validation early
                    submitted = False

                # Dietary Preferences
                st.subheader("Dietary and Allergies")
                selected_diet_prefs = st.multiselect("Dietary Preferences", dietary_preferences, default=dietary_prefs_val)
                custom_diet_prefs_input = st.text_area("Custom Dietary Preferences (comma separated)", value=custom_prefs_val, help="Enter multiple custom dietary preferences separated by commas. Example: Carnivore, Lacto-Vegan, Flexitarian")
                selected_allergies = st.multiselect("Allergies", all_allergies, default=[a for a in allergies_val if a in all_allergies])
                custom_allergies_input = st.text_area("Custom Allergies (comma separated)", value=custom_allergies_val, help="Enter multiple custom allergies separated by commas. Example: Peanuts, Shellfish, Kiwi")

                # Preferred Servings
                preferred_servings_input = st.number_input("Preferred Servings", min_value=1, value=preferred_servings_val, help="How many people you typically cook for or want meals scaled to.")

                # Emergency Supply Goal
                emergency_supply_goal_input = st.number_input(
                    "Emergency Supply Goal (days)",
                    min_value=0,
                    value=emergency_supply_goal_val,
                    help="How many days of emergency supplies you want to keep?"
                )

                # Language and Timezone
                st.subheader("Preferences")
                preferred_lang = st.selectbox("Preferred Language", language_labels, index=language_labels.index(current_language_label))
                selected_language_code = language_keys[language_labels.index(preferred_lang)]
                selected_timezone = st.selectbox('Time Zone', options=timezones, index=timezones.index(timezone_val))

                # Email Settings
                email_daily_choice = st.radio("Receive daily cooking instructions?", ('Yes', 'No'),
                                              index=0 if email_daily_inst_val else 1)
                email_plan_saved_choice = st.radio("Receive a shopping list when your meal plan is saved or updated?", ('Yes', 'No'),
                                                   index=0 if email_meal_plan_saved_val else 1)
                email_instr_gen_choice = st.radio("Receive an email when you request cooking instructions?", ('Yes', 'No'),
                                                  index=0 if email_instr_gen_val else 1)

                # Goals
                st.subheader("User Goals")
                if goal_data:
                    st.write(f"**{goal_data['goal_name']}**: {goal_data['goal_description']}")
                else:
                    st.info("No goals set yet.")

                goal_name = st.text_input("Goal Name", value=goal_data['goal_name'] if goal_data else "")
                goal_description = st.text_area("Goal Description", value=goal_data['goal_description'] if goal_data else "")

                submitted = st.form_submit_button("Update Profile")

                if submitted:
                    if (valid_username if username_input else True) and (valid_email if email_input else True) and (valid_phone if phone_input else True):
                        # Parse custom preferences
                        custom_prefs_list = [p.strip() for p in custom_diet_prefs_input.split(',') if p.strip()]
                        custom_allergies_list = [a.strip() for a in custom_allergies_input.split(',') if a.strip()]

                        profile_data = {
                            'username': username_input,
                            'email': email_input,
                            'phone_number': phone_input,
                            'dietary_preferences': selected_diet_prefs,
                            'custom_dietary_preferences': custom_prefs_list,
                            'allergies': selected_allergies,
                            'custom_allergies': custom_allergies_list,
                            'timezone': selected_timezone,
                            'preferred_language': selected_language_code,
                            'email_daily_instructions': (email_daily_choice == 'Yes'),
                            'email_meal_plan_saved': (email_plan_saved_choice == 'Yes'),
                            'email_instruction_generation': (email_instr_gen_choice == 'Yes'),
                            'preferred_servings': preferred_servings_input,
                            'emergency_supply_goal': emergency_supply_goal_input,
                            'address': {
                                'street': street_input,
                                'city': city_input,
                                'state': state_input,
                                'postalcode': postal_input,
                                'country': country_selected
                            }
                        }

                        # Update the profile via API
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
                            # Refresh session state user info after update
                            fetch_and_update_user_profile()
                            # Navigate back to home
                            st.switch_page("views/home.py")
                        else:
                            error_data = update_response.json()
                            if isinstance(error_data, dict):
                                st.error("Profile update failed. Please fix the following issues:")
                                for field, messages in error_data.items():
                                    field_name = field.replace('_', ' ').title()
                                    if isinstance(messages, list):
                                        st.warning(f"**{field_name}**: {', '.join(messages)}")
                                    else:
                                        st.warning(f"**{field_name}**: {messages}")
                            else:
                                st.error("Failed to update profile. Please try again later.")

            # Account Deletion Section
            st.subheader("Delete Account")
            st.warning("**This action cannot be undone.** All your data will be permanently deleted.")
            confirmation_input = st.text_input('Type "done eating" to confirm account deletion.', key="delete_confirm")
            password_input = st.text_input("Enter your password", type="password", key="delete_password")

            if st.button("Delete My Account"):
                if confirmation_input == 'done eating' and password_input:
                    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                    response = api_call_with_refresh(
                        url=f'{os.getenv("DJANGO_URL")}/auth/api/delete_account/',
                        headers=headers,
                        method='delete',
                        data={'confirmation': confirmation_input, 'password': password_input}
                    )
                    if response.status_code == 200:
                        st.success("Your account has been deleted successfully.")
                        # Clear session state but preserve navigation
                        navigation_state = st.session_state.get("navigation", None)
                        for key in list(st.session_state.keys()):
                            del st.session_state[key]
                        if navigation_state:
                            st.session_state["navigation"] = navigation_state
                        st.rerun()
                    else:
                        error_message = response.json().get('message', 'Unknown error')
                        st.error(f"Failed to delete account: {error_message}")
                else:
                    st.error('You must type "done eating" exactly and provide your password.')

        else:
            # If the user somehow is authenticated but no role, just show an error or handle gracefully
            st.error("User authentication or role state unclear. Please re-login.")
except Exception as e:
    logging.error(f"An error occurred: {str(e)}")
    st.error("An unexpected error occurred. Please try again later.")

# Add footer
footer()