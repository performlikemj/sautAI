import streamlit as st
import os
import logging
from utils import api_call_with_refresh, is_user_authenticated, login_form, footer, refresh_chef_status

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("error.log"),
    logging.StreamHandler()
])

try:
    # If not logged in, show login form
    if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
        login_form()
        st.stop()

    # If user is already a chef, redirect to chef dashboard
    if st.session_state.get("is_chef", False):
        st.warning("You are already a chef! Redirecting to chef dashboard...")
        st.switch_page("views/8_chef_meals.py")

    # Title and description
    st.title("Chef Application")
    st.info("""
    Thank you for your interest in becoming a chef with sautAI! 
    Please fill out the application form below. We'll review your application and get back to you soon.
    """)

    # Initialize session state for form data if not exists
    if 'chef_application_data' not in st.session_state:
        st.session_state.chef_application_data = {
            'experience': '',
            'bio': '',
            'postal_codes': '',
        }
    if 'chef_application_error' not in st.session_state:
        st.session_state.chef_application_error = None


    # Display error message if exists
    if st.session_state.chef_application_error:
        st.error(st.session_state.chef_application_error)
        # Clear error after displaying
        st.session_state.chef_application_error = None

    # Application form
    with st.form("chef_application_form"):
        # Culinary Experience
        st.subheader("Culinary Experience")
        experience = st.text_area(
            "Tell us about your culinary experience",
            value=st.session_state.chef_application_data['experience'],
            placeholder="Share your cooking experience, training, and any relevant certifications...",
            help="Include details about your cooking experience, any formal training, and relevant certifications."
        )

        # Bio
        st.subheader("About You")
        bio = st.text_area(
            "Tell us about yourself",
            value=st.session_state.chef_application_data['bio'],
            placeholder="Share your story, cooking style, and what makes you unique as a chef...",
            help="Tell us about your cooking style, inspiration, and what makes you unique as a chef."
        )

        # Profile Picture
        st.subheader("Profile Picture")
        profile_pic = st.file_uploader(
            "Upload a professional photo of yourself",
            type=['jpg', 'jpeg', 'png'],
            help="Upload a professional photo that represents you as a chef."
        )

        # Serving Areas
        st.subheader("Serving Areas")
        postal_codes = st.text_input(
            "Postal Codes You Plan to Serve",
            value=st.session_state.chef_application_data['postal_codes'],
            placeholder="Enter postal codes separated by commas",
            help="Enter the postal codes of the areas where you plan to serve meals."
        )

        # Submit button
        submitted = st.form_submit_button("Submit Application")

        if submitted:
            # Update session state with current form data
            st.session_state.chef_application_data = {
                'experience': experience,
                'bio': bio,
                'postal_codes': postal_codes,
            }
            if not experience or not bio or not postal_codes:
                st.session_state.chef_application_error = "Please fill in all required fields."
                st.session_state.show_chef_application = True
                st.rerun()
            else:
                # Prepare the data
                data = {
                    'user_id': st.session_state.user_id,
                    'experience': experience,
                    'bio': bio,
                    'postal_codes': [code.strip() for code in postal_codes.split(',') if code.strip()]
                }

                if profile_pic:
                    # Read the actual bytes
                    file_bytes = profile_pic.read()

                    # Decide on a fallback content-type you expect (e.g., 'image/png')
                    # or do a little guess from the extension if needed.
                    content_type = "image/png"
                    if profile_pic.name.lower().endswith("jpg") or profile_pic.name.lower().endswith("jpeg"):
                        content_type = "image/jpeg"

                    files = {
                        "profile_pic": (profile_pic.name, file_bytes, content_type)
                    }
                else:
                    files = None

                # Log request details
                logging.info(f"Submitting chef application with data: {data}")
                if files:
                    logging.info(f"Profile picture details: name={profile_pic.name}, size={profile_pic.size}, type={profile_pic.type}")
                logging.info(f"Using authorization token: {st.session_state.user_info['access'][:10]}...")

                # Submit the request
                headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
                response = api_call_with_refresh(
                    url=f"{os.getenv('DJANGO_URL')}/chefs/api/chefs/submit-chef-request/",
                    method='post',
                    headers=headers,
                    data=data,
                    files=files
                )

                # Log response details
                if response:
                    logging.info(f"Response status code: {response.status_code}")
                    logging.info(f"Response headers: {response.headers}")
                    try:
                        response_data = response.json()
                        logging.info(f"Response data: {response_data}")
                    except Exception as e:
                        logging.error(f"Error parsing response JSON: {str(e)}")
                else:
                    logging.error("No response received from API call")

                if response and response.status_code in [200, 201]:
                    # Clear form data from session state
                    if 'chef_application_data' in st.session_state:
                        del st.session_state.chef_application_data
                    # Store success message in session state to display on profile page
                    st.session_state.chef_application_success = "Your chef application has been submitted successfully! We'll review your application and get back to you soon."
                    # Remove the show_chef_application flag from session state
                    if 'show_chef_application' in st.session_state:
                        del st.session_state.show_chef_application
                    
                    # Refresh chef status in case it was immediately approved (for testing/admin scenarios)
                    refresh_chef_status()
                    
                    # Redirect back to profile page
                    st.switch_page("views/6_profile.py")
                elif response.status_code == 409:
                    st.warning("You already have a pending chef request. Please wait for approval or contact support.")
                    st.session_state.show_chef_application = True
                else:
                    if response:
                        error_message = response.json().get('error', 'Failed to submit application')
                        st.session_state.chef_application_error = error_message
                        st.session_state.show_chef_application = True
                    else:
                        st.session_state.chef_application_error = "Failed to submit application. Please try again later."
                        st.session_state.show_chef_application = True
                    st.rerun()



    # Add a cancel button outside the form
    if st.button("Cancel Application", use_container_width=True):
        # Clear form data from session state
        if 'chef_application_data' in st.session_state:
            del st.session_state.chef_application_data
        # Remove the show_chef_application flag from session state
        if 'show_chef_application' in st.session_state:
            del st.session_state.show_chef_application
        # Redirect back to profile page
        st.switch_page("views/6_profile.py")

except Exception as e:
    logging.error(f"An error occurred: {str(e)}")
    st.error("An unexpected error occurred. Please try again later.")

# Add footer
footer()