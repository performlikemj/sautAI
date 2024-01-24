import streamlit as st
import requests
import os
import datetime
from utils import api_call_with_refresh, is_user_authenticated
from sautai import sidebar_logout


def profile():
    st.title("Profile")
    st.header("Profile")

    # Logout Button
    if 'is_logged_in' in st.session_state and st.session_state['is_logged_in']:
        sidebar_logout()
    
    # Check if user is logged in
    if 'user_info' in st.session_state and st.session_state.user_info:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        user_details = requests.get(f'{os.getenv("DJANGO_URL")}/auth/api/user_details/', headers=headers)
        if user_details.status_code == 200:
            user_data = user_details.json()
            st.session_state.user_id = user_data.get('id')  # Set user_id in session state
            # ... rest of your code for displaying and updating profile ...
        else:
            user_data = {}

        if is_user_authenticated():
            # Define a container for each field
            username_container = st.container()
            email_container = st.container()
            phone_container = st.container()
            diet_container = st.container()
            allergy_container = st.container()
            goal_container = st.container()
            address_container = st.container()
            # Goal management section
            with goal_container:
                st.header("Manage Your Goals")
                # Fetch current goal
                goal_response = api_call_with_refresh(
                    url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/user_goal/',
                    method='get',
                    headers={'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                )
                current_goal = goal_response.json() if goal_response.status_code == 200 else {}
                goal_name = st.text_input("Goal Name", value=current_goal.get('goal_name', ''))
                goal_description = st.text_area("Goal Description", value=current_goal.get('goal_description', ''))


                if st.button("Update Goal"):
                    goal_data = {
                        "goal_name": goal_name,
                        "goal_description": goal_description
                    }
                    update_goal_response = api_call_with_refresh(
                        url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/goal_management/',
                        method='post',
                        data=goal_data,
                        headers={'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                    )
                    if update_goal_response.status_code == 200:
                        st.success("Goal updated successfully!")
                    else:
                        st.error("Failed to update goal.")    

            # Username field
            with username_container:
                username = st.text_input("Username", value=user_data.get('username', ''))
                if st.button("Update Username"):
                    update_response = api_call_with_refresh(
                        url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/auth/api/update_profile/',
                        method='post',
                        data={'username': username},
                        headers={'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                    )
                    if update_response.status_code == 200:                    
                        st.success("Username updated successfully!")

            # Email field
            with email_container:
                email = st.text_input("Email", value=user_data.get('email', ''))
                if st.button("Update Email"):
                    update_response = api_call_with_refresh(
                        url=f'{os.getenv("DJANGO_URL")}/auth/api/update_profile/',
                        method='post',
                        data={'email': email},
                        headers={'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                    )
                    if update_response.status_code == 200:
                        st.success("Email updated successfully!")

            # Phone number field
            with phone_container:
                phone_number = st.text_input("Phone Number", value=user_data.get('phone_number', ''))
                if st.button("Update Phone Number"):
                    update_response = api_call_with_refresh(
                        url=f'{os.getenv("DJANGO_URL")}/auth/api/update_profile/',
                        method='post',
                        data={'phone_number': phone_number},
                        headers={'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                    )
                    if update_response.status_code == 200:
                        st.success("Phone number updated successfully!")

            # Dietary preference field
            with diet_container:
                dietary_preferences = ['Vegan', 'Vegetarian', 'Pescatarian', 'Gluten-Free', 'Keto', 'Paleo', 'Halal', 'Kosher', 'Low-Calorie', 'Low-Sodium', 'High-Protein', 'Dairy-Free', 'Nut-Free', 'Raw Food', 'Whole 30', 'Low-FODMAP', 'Diabetic-Friendly', 'Everything']

                user_dietary_pref = user_data.get('dietary_preference', '')
                index = 0  # Default index
                if user_dietary_pref in dietary_preferences:
                    index = dietary_preferences.index(user_dietary_pref)

                dietary_preference = st.selectbox("Dietary Preference", dietary_preferences, index=index)
                if st.button("Update Dietary Preference"):
                    update_response = api_call_with_refresh(
                        url=f'{os.getenv("DJANGO_URL")}/auth/api/update_profile/',
                        method='post',
                        data={'dietary_preference': dietary_preference},
                        headers={'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                    )
                    if update_response.status_code == 200:                    
                        st.success("Dietary preference updated successfully!")
            with allergy_container:
                allergies = [
                    'Peanuts', 
                    'Tree nuts', 
                    'Milk', 
                    'Egg', 
                    'Wheat', 
                    'Soy', 
                    'Fish', 
                    'Shellfish', 
                    'Sesame', 
                    'Mustard', 
                    'Celery', 
                    'Lupin', 
                    'Sulfites', 
                    'Molluscs', 
                    'Corn', 
                    'Gluten', 
                    'Kiwi', 
                    'Latex', 
                    'Pine Nuts', 
                    'Sunflower Seeds', 
                    'Poppy Seeds', 
                    'Fennel', 
                    'Peach', 
                    'Banana', 
                    'Avocado', 
                    'Chocolate', 
                    'Coffee', 
                    'Cinnamon', 
                    'Garlic', 
                    'Chickpeas', 
                    'Lentils', 
                    'None'
                ]
                user_allergy = user_data.get('allergy', '')
                index = 0
                if user_allergy in allergies:
                    index = allergies.index(user_allergy)
                allergy = st.selectbox("Allergy", allergies, index=index)
                if st.button("Update Allergy"):
                    update_response = api_call_with_refresh(
                        url=f'{os.getenv("DJANGO_URL")}/auth/api/update_profile/',
                        method='post',
                        data={'allergy': allergy},
                        headers={'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                    )
                    if update_response.status_code == 200:                    
                        st.success("Allergy updated successfully!")
            with address_container:
                # Fetch current address
                address_response = api_call_with_refresh(
                    url=f'{os.getenv("DJANGO_URL")}/auth/api/address_details/',
                    method='get',
                    headers={'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                )
                current_address = address_response.json() if address_response.status_code == 200 else {}

                # Input fields for address
                street = st.text_input("Street", value=current_address.get('street', ''))
                city = st.text_input("City", value=current_address.get('city', ''))
                state = st.text_input("State", value=current_address.get('state', ''))
                postalcode = st.text_input("Postal Code", value=current_address.get('input_postalcode', ''))
                country = st.text_input("Country", value=current_address.get('country', ''))

                if st.button("Update Address"):
                    address_data = {
                        "street": street,
                        "city": city,
                        "state": state,
                        "input_postalcode": postalcode,
                        "country": country
                    }
                    update_address_response = api_call_with_refresh(
                    url=f'{os.getenv("DJANGO_URL")}/auth/api/update_profile/',
                        method='post',
                        data=address_data,
                        headers={'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                    )
                    if update_address_response.status_code == 200:
                        st.success("Address updated successfully!")
                    elif update_address_response.status_code == 400 and not update_address_response.json().get('is_served'):
                        print(update_address_response.json())
                        st.error("We do not currently serve your area.")
                    else:
                        st.error("Failed to update address.")
    else:
        # User is not logged in, display a message or redirect
        st.warning("Please log in to view and update your profile.")

if __name__ == "__main__":
    profile()
