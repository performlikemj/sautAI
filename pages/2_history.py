# pages/history.py
import streamlit as st
import requests
from dotenv import load_dotenv
load_dotenv()
import os
from utils import api_call_with_refresh
from datetime import datetime



st.set_page_config(
    page_title="sautAI",
    page_icon="🥘",
    layout="wide",
    initial_sidebar_state="auto",
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

if __name__ == "__main__":
    threads()