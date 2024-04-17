import streamlit as st
import requests
import os
import datetime
from utils import api_call_with_refresh, is_user_authenticated, login_form, toggle_chef_mode

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
    if 'current_role' in st.session_state and st.session_state['current_role'] != 'chef':
        st.title("Profile")

        # Check if user is logged in
        if 'user_info' in st.session_state and st.session_state.user_info:
            headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
            user_details = requests.get(f'{os.getenv("DJANGO_URL")}/auth/api/user_details/', headers=headers)
            if user_details.status_code == 200:
                user_data = user_details.json()
                print(f'User data: {user_data}')
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
                with st.form("profile_update_form"):
                    username = st.text_input("Username", value=user_data.get('username', ''))
                    email = st.text_input("Email", value=user_data.get('email', ''))
                    phone_number = st.text_input("Phone Number", value=user_data.get('phone_number', ''))
                    dietary_preferences = [
                        'Everything', 'Vegetarian', 'Pescatarian', 'Gluten-Free', 'Keto', 
                        'Paleo', 'Halal', 'Kosher', 'Low-Calorie', 'Low-Sodium', 'High-Protein', 
                        'Dairy-Free', 'Nut-Free', 'Raw Food', 'Whole 30', 'Low-FODMAP', 
                        'Diabetic-Friendly', 'Vegan'
                    ]
                    dietary_preference = st.selectbox("Dietary Preference", dietary_preferences, index=dietary_preferences.index(user_data.get('dietary_preference', 'Everything')))
                    allergies = [
                        'Peanuts', 'Tree nuts', 'Milk', 'Egg', 'Wheat', 'Soy', 'Fish', 'Shellfish', 'Sesame', 'Mustard', 
                        'Celery', 'Lupin', 'Sulfites', 'Molluscs', 'Corn', 'Gluten', 'Kiwi', 'Latex', 'Pine Nuts', 
                        'Sunflower Seeds', 'Poppy Seeds', 'Fennel', 'Peach', 'Banana', 'Avocado', 'Chocolate', 
                        'Coffee', 'Cinnamon', 'Garlic', 'Chickpeas', 'Lentils'
                    ]
                    default_allergies = user_data.get('allergies', [])
                    valid_default_allergies = [allergy for allergy in default_allergies if allergy in allergies]
                    selected_allergies = st.multiselect("Allergies", allergies, default=valid_default_allergies)                    
                    street = st.text_input("Street", value=user_data.get('street', ''))
                    city = st.text_input("City", value=user_data.get('city', ''))
                    state = st.text_input("State", value=user_data.get('state', ''))
                    postalcode = st.text_input("Postal Code", value=user_data.get('postalcode', ''))
                    country = st.text_input("Country", value=user_data.get('country', ''))

                    submitted = st.form_submit_button("Update Profile")
                    if submitted:
                        profile_data = {
                            'username': username,
                            'email': email,
                            'phone_number': phone_number,
                            'dietary_preference': dietary_preference,
                            'allergies': selected_allergies,
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
                        else:
                            st.error(f"Failed to update profile: {update_response.text}")
        else:
            # User is not logged in, display a message or redirect
            st.warning("Please log in to view and update your profile.")

if __name__ == "__main__":
    profile()
