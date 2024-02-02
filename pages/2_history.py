# pages/history.py
import streamlit as st
import requests
from dotenv import load_dotenv
load_dotenv()
import os
from utils import api_call_with_refresh
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='history.log', # Log to a file. Remove this to log to console
                    filemode='w') # 'w' to overwrite the log file on each run, 'a' to append

# Example usage
logging.info("Starting the Streamlit app")

st.set_page_config(
    page_title="sautAI - Your Diet and Nutrition Guide",
    page_icon="🥗", 
    initial_sidebar_state="expanded",
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

def thread_detail(thread_id):
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
    response = api_call_with_refresh(
        url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/thread_detail/{thread_id}/',
        method='get',
        headers=headers
    )
    if response.status_code == 200:
        chat_history = response.json().get('chat_history', [])
        
        # Sort chat_history by 'created_at' key
        chat_history.sort(key=lambda x: x['created_at'])

        for msg in chat_history:
            with st.chat_message(msg['role']):
                st.markdown(msg['content'])
    else:
        st.error("Error fetching thread details.")



def threads():
    st.title("Chat History")
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
                    st.switch_page("pages/1_assistant.py")
                else:
                    st.error("Invalid username or password.")
            if register_button:
                st.switch_page("pages/5_register.py")
                    

            # Password Reset Button
            if st.button("Forgot your password?"):
                # Directly navigate to the activate page for password reset
                st.switch_page("pages/4_account.py")

    try:
        if 'is_logged_in' in st.session_state and st.session_state.is_logged_in:
            # Initialize or update current page in session state
            current_page = st.session_state.get('current_page', 1)
        
            # Initialize pagination variables
            prev_page = False
            next_page = False
            # Fetch chat threads
            headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
            response = api_call_with_refresh(
                url=f'{os.getenv("DJANGO_URL")}/customer_dashboard/api/thread_history/?page={current_page}',
                method='get',
                headers=headers
            )

            if response.status_code == 200:
                chat_threads_response = response.json()
                chat_threads = chat_threads_response['results']
                st.write("Your recent chat history:")

                # Pagination buttons
                col1, col2 = st.columns(2)
                with col1:
                    if chat_threads_response['previous']:
                        prev_page = st.button('Previous page', key='previous_page')
                with col2:
                    if chat_threads_response['next']:
                        next_page = st.button('Next page', key='next_page')

                if prev_page:
                    st.session_state.current_page = max(1, current_page - 1)
                if next_page:
                    st.session_state.current_page = current_page + 1

                # Refresh the page after pagination button click
                if prev_page or next_page:
                    st.experimental_rerun()

                # Displaying each chat thread
                for thread in chat_threads:
                    # Parse the date string into a datetime object
                    created_at = datetime.strptime(thread['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ")

                    # Format the datetime object into a string
                    formatted_date = created_at.strftime("%B %d, %Y - %H:%M:%S")

                    st.write(formatted_date)

                    # Toggle thread detail view
                    if st.button(thread['title'], key=thread['id']):
                        if st.session_state.get('selected_thread_id') == thread['openai_thread_id']:
                            # Toggle off if the same thread is clicked again
                            st.session_state.selected_thread_id = None
                        else:
                            # Show new thread details
                            st.session_state.selected_thread_id = thread['openai_thread_id']
                            thread_detail(thread['openai_thread_id'])

                    # Check if thread details should be displayed
                    if st.session_state.get('selected_thread_id') == thread['openai_thread_id']:
                        thread_detail(thread['openai_thread_id'])

                    # Add a divider after each thread
                    st.divider()
            else:
                st.error("Error fetching threads.")
        else:
            st.warning("Please log in to view your threads.")
    except Exception as e:
        st.error("An Error occurred. We are looking into it.")
        logging.error("Error occurred", exc_info=True)


if __name__ == "__main__":
    threads()
