# pages/history.py
import streamlit as st
import requests
from dotenv import load_dotenv
load_dotenv()
import os
from utils import api_call_with_refresh, login_form, toggle_chef_mode, resend_activation_link
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.WARNING,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename='history.log', # Log to a file. Remove this to log to console
                    filemode='w') # 'w' to overwrite the log file on each run, 'a' to append


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
        st.title("Chat History")

        try:
            if 'is_logged_in' in st.session_state and st.session_state.is_logged_in:
                # Check if the user's email is confirmed
                if not st.session_state.get('email_confirmed', False):
                    st.warning("Your email address is not confirmed. Please confirm your email to access your chat history.")
                    if st.button("Resend Activation Link"):
                        resend_activation_link(st.session_state['user_id'])
                    return
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
                        st.rerun()

                    # Displaying each chat thread
                    for thread in chat_threads:
                        # Parse the date string into a datetime object
                        created_at = datetime.strptime(thread['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ")

                        # Format the datetime object into a string
                        formatted_date = created_at.strftime("%B %d, %Y - %H:%M:%S")

                        st.write(formatted_date)


                        # Button to continue the conversation on the assistant page
                        if st.button(thread['title'], key=thread['id']):
                            st.session_state.selected_thread_id = thread['openai_thread_id']
                            st.switch_page("pages/1_assistant.py")

                        st.divider()
                else:
                    st.error("Error fetching history.")
            else:
                st.warning("Please log in to view your history.")
        except Exception as e:
            st.error("An Error occurred. We are looking into it.")
            logging.error("Error occurred", exc_info=True)


if __name__ == "__main__":
    threads()
