import streamlit as st
import requests
import os
import datetime
from utils import api_call_with_refresh, is_user_authenticated

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

def profile():
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
                    st.rerun()
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
            
    st.title("Profile")

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
                dietary_preferences = ['Everything', 'Vegetarian', 'Pescatarian', 'Gluten-Free', 'Keto', 'Paleo', 'Halal', 'Kosher', 'Low-Calorie', 'Low-Sodium', 'High-Protein', 'Dairy-Free', 'Nut-Free', 'Raw Food', 'Whole 30', 'Low-FODMAP', 'Diabetic-Friendly', 'Vegan']

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
                user_allergy = user_data.get('allergies', '')
                index = 0
                if user_allergy in allergies:
                    index = allergies.index(user_allergy)
                allergy = st.selectbox("Allergy", allergies, index=index)
                if st.button("Update Allergy"):
                    update_response = api_call_with_refresh(
                        url=f'{os.getenv("DJANGO_URL")}/auth/api/update_profile/',
                        method='post',
                        data={'allergies': allergy},
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
