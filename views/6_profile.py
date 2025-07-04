import pytz
import streamlit as st
import requests
import os
import datetime
import logging
from utils import (api_call_with_refresh, is_user_authenticated, login_form, toggle_chef_mode, 
                  fetch_and_update_user_profile, validate_input, resend_activation_link, footer,
                  fetch_languages, refresh_chef_status)

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
    # Check if we need to redirect to chef application
    if st.session_state.get("show_chef_application", False):
        st.switch_page("views/chef_application.py")
    else:
        # If it exists in session state but we didn't switch pages, clear it.
        if 'show_chef_application' in st.session_state:
            del st.session_state['show_chef_application']

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
            
            # Display chef application success message if it exists
            if 'chef_application_success' in st.session_state:
                st.success(st.session_state.chef_application_success)
                del st.session_state.chef_application_success

            # Fetch user details
            headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
            user_details = api_call_with_refresh(f'{os.getenv("DJANGO_URL")}/auth/api/user_details/', method='get', headers=headers)
            address_details = api_call_with_refresh(f'{os.getenv("DJANGO_URL")}/auth/api/address_details/', method='get', headers=headers)
            countries_details = api_call_with_refresh(f'{os.getenv("DJANGO_URL")}/auth/api/countries/', method='get', headers=headers)
            
            if user_details.status_code == 200:
                user_data = user_details.json()
                st.session_state.user_id = user_data.get('id')
                personal_assistant_email = user_data.get('personal_assistant_email')
                if personal_assistant_email:
                    st.markdown(f"""
                    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 20px;">
                        <h5 style="margin-bottom: 5px;">Your Personal Assistant Contact</h5>
                        <p style="margin-bottom: 0;">📧 <a href="mailto:{personal_assistant_email}">{personal_assistant_email}</a></p>
                    </div>
                    """, unsafe_allow_html=True)
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
            unsubscribed_from_emails_val = user_data.get('unsubscribed_from_emails', False)
            household_member_count_val = user_data.get('household_member_count', 1)
            household_members_val = user_data.get('household_members', [])
            emergency_supply_goal_val = user_data.get('emergency_supply_goal', st.session_state.get('emergency_supply_goal', 0))

            street_val = address_data.get('street', '')
            city_val = address_data.get('city', '')
            state_val = address_data.get('state', '')
            postal_val = address_data.get('postalcode', address_data.get('input_postalcode', ''))
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

            # Debug: Show current household members in session state
            if st.session_state.get('household_members'):
                with st.expander("🔍 Debug: Current Household Members in Session", expanded=False):
                    st.json(st.session_state['household_members'])
                    st.caption(f"Count in session: {len(st.session_state.get('household_members', []))}")
            
            # Fetch available languages from API
            languages = fetch_languages()
            
            # Find the current language in the languages list
            current_language_display = None
            current_language_index = 0
            
            for i, lang in enumerate(languages):
                if lang['code'] == preferred_language_val:
                    current_language_display = f"{lang['name']} ({lang['name_local']})"
                    current_language_index = i
                    break
            
            # If not found, default to English or first language
            if current_language_display is None:
                for i, lang in enumerate(languages):
                    if lang['code'] == 'en':
                        current_language_display = f"{lang['name']} ({lang['name_local']})"
                        current_language_index = i
                        break
                
                # If English not found either, use the first language
                if current_language_display is None and languages:
                    lang = languages[0]
                    current_language_display = f"{lang['name']} ({lang['name_local']})"
                    current_language_index = 0

            # Create language display options
            language_display_options = [f"{lang['name']} ({lang['name_local']})" for lang in languages]
            language_codes = [lang['code'] for lang in languages]

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

                # Household Member Count
                household_member_count_input = st.number_input(
                    "Household Members",
                    min_value=1,
                    value=household_member_count_val,
                    help="How many people live in your household?"
                )

                # Create household member input fields
                # Values will be automatically stored in session state with the keys
                for i in range(int(household_member_count_input)):
                    existing = household_members_val[i] if i < len(household_members_val) else {}
                    with st.expander(f"Household Member {i+1} (optional)"):
                        st.text_input("Name", value=existing.get('name', ''), key=f"profile_member_name_{i}")
                        st.number_input("Age", min_value=0, value=existing.get('age', 0) or 0, step=1, key=f"profile_member_age_{i}")
                        st.multiselect(
                            "Dietary Preferences",
                            dietary_preferences,
                            default=existing.get('dietary_preferences', []),
                            key=f"profile_member_diet_{i}"
                        )
                        st.text_area("Notes", value=existing.get('notes', ''), key=f"profile_member_notes_{i}")
                
                # Debug: Show current form values before submission
                if household_member_count_input > 1:
                    with st.expander("🔍 Debug: Current Form Values", expanded=False):
                        st.write("**Household Members Form Data:**")
                        for i in range(int(household_member_count_input)):
                            name = st.session_state.get(f"profile_member_name_{i}", '')
                            age = st.session_state.get(f"profile_member_age_{i}", 0)
                            dietary_prefs = st.session_state.get(f"profile_member_diet_{i}", [])
                            notes = st.session_state.get(f"profile_member_notes_{i}", '')
                            
                            if name or age or dietary_prefs or notes:
                                st.json({
                                    f"Member {i+1}": {
                                        "name": name,
                                        "age": age,
                                        "dietary_preferences": dietary_prefs,
                                        "notes": notes
                                    }
                                })
                        st.caption("This shows what data will be submitted when you click 'Update Profile'")

                # Emergency Supply Goal
                emergency_supply_goal_input = st.number_input(
                    "Emergency Supply Goal (days)",
                    min_value=0,
                    value=emergency_supply_goal_val,
                    help="How many days of emergency supplies you want to keep?"
                )

                # Language and Timezone
                st.subheader("Preferences")
                preferred_lang = st.selectbox(
                    "Preferred Language", 
                    language_display_options, 
                    index=current_language_index,
                    help="Select your preferred language for the application"
                )
                selected_language_code = language_codes[language_display_options.index(preferred_lang)]
                selected_timezone = st.selectbox('Time Zone', options=timezones, index=timezones.index(timezone_val))

                # Email Settings
                st.subheader("Email Preferences")
                receive_emails_choice = st.radio("Receive emails from sautAI?", ('Yes', 'No'),
                                              index=0 if not unsubscribed_from_emails_val else 1,
                                              help="When set to 'No', you will not receive any emails including daily cooking instructions, shopping lists, or cooking instructions.")

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

                        # Process household members data during form submission using session state
                        household_members_input = []
                        for i in range(int(household_member_count_input)):
                            # Access values from session state using the widget keys
                            name = st.session_state.get(f"profile_member_name_{i}", '')
                            age = st.session_state.get(f"profile_member_age_{i}", 0)
                            dietary_prefs = st.session_state.get(f"profile_member_diet_{i}", [])
                            notes = st.session_state.get(f"profile_member_notes_{i}", '')
                            
                            # Clean up the data - ensure proper types and handle empty values
                            member_data = {
                                'name': str(name).strip() if name else '',
                                'age': int(age) if age and age > 0 else None,
                                'dietary_preferences': list(dietary_prefs) if dietary_prefs else [],
                                'notes': str(notes).strip() if notes else '',
                            }
                            household_members_input.append(member_data)
                            logging.info(f"Member {i+1} processed data: {member_data}")
                        
                        # Filter out completely empty members (no name, age, prefs, or notes)
                        filtered_members = []
                        for member in household_members_input:
                            if (member['name'] or member['age'] or member['dietary_preferences'] or member['notes']):
                                filtered_members.append(member)
                        
                        household_members_input = filtered_members
                        logging.info(f"Final household members after filtering: {household_members_input}")

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
                            'unsubscribed_from_emails': (receive_emails_choice == 'No'),
                            'household_member_count': household_member_count_input,
                            'household_members': household_members_input,
                            'emergency_supply_goal': emergency_supply_goal_input,
                            'address': {
                                'street': street_input,
                                'city': city_input,
                                'state': state_input,
                                'postalcode': postal_input,
                                'input_postalcode': postal_input,
                                'country': country_selected
                            }
                        }

                        # Add debug logging for household members
                        logging.info(f"Household member count: {household_member_count_input}")
                        logging.info(f"Available session state keys: {[k for k in st.session_state.keys() if 'profile_member' in k]}")
                        logging.info(f"Submitting household members data: {household_members_input}")
                        logging.info(f"Full profile data being sent: {profile_data}")
                        
                        # Update the profile via API
                        update_response = api_call_with_refresh(
                            url=f'{os.getenv("DJANGO_URL")}/auth/api/update_profile/',
                            method='post',
                            data=profile_data,
                            headers={'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                        )
                        
                        # Log the response for debugging
                        logging.info(f"Profile update response status: {update_response.status_code}")
                        if update_response.status_code == 200:
                            response_data = update_response.json()
                            logging.info(f"Profile update response data: {response_data}")
                        else:
                            logging.error(f"Profile update failed with response: {update_response.text}")
                        if update_response.status_code == 200:
                            st.success("Profile updated successfully!")
                            
                            # Update session state immediately with the submitted data
                            st.session_state['household_member_count'] = household_member_count_input
                            st.session_state['household_members'] = household_members_input
                            logging.info(f"Updated session state with household members: {household_members_input}")
                            
                            if goal_name and goal_description:
                                if update_goal(goal_name, goal_description):
                                    st.success("Goal updated successfully!")
                                else:
                                    st.error("Failed to update goal.")
                            
                            # Refresh session state user info after update to sync with backend
                            fetch_and_update_user_profile()
                            
                            # Verify the data was properly saved
                            if 'household_members' in st.session_state:
                                logging.info(f"Session state after refresh: {st.session_state['household_members']}")
                                saved_count = len(st.session_state['household_members'])
                                if saved_count > 0:
                                    st.success(f"✅ Household members saved: {saved_count} member(s)")
                                    # Show saved members for verification
                                    for i, member in enumerate(st.session_state['household_members']):
                                        if member.get('name'):
                                            st.caption(f"Member {i+1}: {member['name']} (Age: {member.get('age', 'Not specified')})")
                                else:
                                    st.info("ℹ️ No household members saved (only main user)")
                            else:
                                st.warning("⚠️ Could not verify household members data in session state")
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

            # Chef Application Section
            st.subheader("Become a Chef")
            
            # Check if user is already a chef
            if st.session_state.get("is_chef", False):
                st.success("You are already a chef! You can access the chef dashboard from the main menu.")
            else:
                st.info("""
                Join a futuristic food cooperative where your culinary talents nourish and empower your community.
                
                As a chef with sautAI, you can:
                
                - Design and manage personalized meal plans tailored to your community's tastes and needs.
                - Serve fresh, delicious meals from convenient community-focused locations.
                - Set flexible pricing that makes healthy food accessible while ensuring fair compensation.
                - Build your culinary reputation and gain recognition for your creativity and skill.
                - Earn income by making a positive, direct impact on your neighbors' lives.
                
                Become a part of the future of food—where innovation meets community collaboration.
                """)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Apply to Become a Chef", use_container_width=True):
                        st.session_state.show_chef_application = True
                        st.rerun()
                
                with col2:
                    if st.button("🔄 Refresh Chef Status", use_container_width=True, help="Check if your chef application has been approved"):
                        with st.spinner("Checking chef status..."):
                            if refresh_chef_status():
                                st.success("Chef status updated!")
                                st.rerun()
                            else:
                                st.info("No changes to your chef status.")

        else:
            # If the user somehow is authenticated but no role, just show an error or handle gracefully
            st.error("User authentication or role state unclear. Please re-login.")
except Exception as e:
    logging.error(f"An error occurred: {str(e)}")
    st.error("An unexpected error occurred. Please try again later.")

# Add footer
footer()