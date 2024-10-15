import streamlit as st
import pandas as pd
from utils import (
    api_call_with_refresh,
    login_form,
    toggle_chef_mode,
    is_user_authenticated,
    resend_activation_link
)
import os
from dotenv import load_dotenv
from datetime import datetime as dt, date
import logging
import math
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("error.log"),
        logging.StreamHandler()
    ]
)

def parse_expiration_date(date_str):
    try:
        return dt.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        logging.warning(f"Invalid date format: {date_str}")
        return None

def pantry_page():
    # Initialize session state for form visibility
    if 'show_add_form' not in st.session_state:
        st.session_state.show_add_form = False

    # Logout Button
    if 'is_logged_in' in st.session_state and st.session_state['is_logged_in']:
        if st.button("Logout", key='pantry_logout'):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("Logged out successfully!")
            st.rerun()
        # Toggle chef mode if needed
        toggle_chef_mode()

    try:
        if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
            login_form()

        # Check if the user is authenticated and email is confirmed
        if is_user_authenticated() and st.session_state.get('email_confirmed', False):
            if 'current_role' in st.session_state and st.session_state['current_role'] != 'chef':
                st.title("Your Pantry")

            # Initialize page number
            if 'pantry_page_number' not in st.session_state:
                st.session_state.pantry_page_number = 1

            # Fetch pantry items with pagination
            headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
            response = api_call_with_refresh(
                url=f'{os.getenv("DJANGO_URL")}/meals/api/pantry-items/?page={st.session_state.pantry_page_number}',
                method='get',
                headers=headers,
            )

            if response and response.status_code == 200:
                pantry_data = response.json()
                pantry_items = pantry_data.get('results', [])
                pantry_records = []

                for item in pantry_items:
                    pantry_records.append({
                        'ID': item['id'],
                        'Item Name': item['item_name'],
                        'Quantity': item['quantity'],
                        'Expiration Date': parse_expiration_date(item['expiration_date']),
                        'Item Type': item['item_type'],
                        'Notes': item['notes'],
                    })

                if not pantry_records:
                    st.info("No pantry items found.")
                else:
                    pantry_df = pd.DataFrame(pantry_records)

                    # Add a 'Delete' column with default False
                    pantry_df['Delete'] = False

                    # Store the original DataFrame in session state
                    st.session_state['original_pantry_df'] = pantry_df.copy()

                    # Display the editable pantry items
                    edited_df = st.data_editor(
                        pantry_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            'Quantity': st.column_config.NumberColumn('Quantity', min_value=0, step=1),
                            'Expiration Date': st.column_config.DateColumn('Expiration Date'),
                            'Item Type': st.column_config.SelectboxColumn('Item Type', options=['Canned', 'Dry']),
                            'Notes': st.column_config.TextColumn('Notes'),
                            'Delete': st.column_config.CheckboxColumn('Delete', default=False)  # Add Delete checkbox
                        },
                        num_rows="dynamic",  # Allow adding/deleting rows
                        key='pantry_data_editor',
                    )

                    # Store the edited DataFrame in session state
                    st.session_state['edited_pantry_df'] = edited_df

                    # Add Submit and Cancel buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button('Submit Changes', key='submit_changes_button'):
                            process_changes(
                                original_df=st.session_state['original_pantry_df'],
                                edited_df=st.session_state['edited_pantry_df']
                            )
                            # After processing changes, reload the page to fetch updated data
                            st.success("Changes submitted successfully!")
                            st.rerun()
                    with col2:
                        if st.button('Cancel Changes', key='cancel_changes_button'):
                            # Discard changes and reload the original data
                            st.session_state['edited_pantry_df'] = st.session_state['original_pantry_df']
                            st.warning("Changes have been discarded.")
                            st.rerun()

                # Pagination Controls
                st.markdown("---")
                col_prev, col_info, col_next = st.columns([1, 2, 1])
                with col_prev:
                    if st.button('Previous Page', key='previous_page_button') and pantry_data.get('previous'):
                        st.session_state.pantry_page_number -= 1
                        st.rerun()
                with col_next:
                    if st.button('Next Page', key='next_page_button') and pantry_data.get('next'):
                        st.session_state.pantry_page_number += 1
                        st.rerun()

                total_pages = math.ceil(pantry_data.get('count', 0) / 10)
                st.write(f"Page {st.session_state.pantry_page_number} of {total_pages}")

            elif response and response.status_code == 401:
                st.error("Unauthorized access. Please log in again.")
                logging.error(f"Failed to fetch pantry items. Status code: {response.status_code}, Response: {response.text}")
            else:
                st.error("Error fetching pantry items.")
                logging.error(f"Failed to fetch pantry items. Status code: {response.status_code if response else 'No Response'}, Response: {response.text if response else 'No Response'}")

            # Show add pantry item form
            if not pantry_records or st.button("Add New Pantry Item", key='show_add_pantry_item_form'):
                st.session_state.show_add_form = True

            if st.session_state.show_add_form:
                with st.form(key='add_pantry_item_form'):
                    item_name = st.text_input("Item Name")
                    quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
                    expiration_date = st.date_input("Expiration Date", value=date.today())
                    item_type = st.selectbox("Item Type", options=['Canned', 'Dry'])
                    notes = st.text_area("Notes")

                    add_item_submit = st.form_submit_button("Add Item")
                    if add_item_submit:
                        # Prepare the new item data
                        new_item = {
                            'Item Name': item_name,
                            'Quantity': quantity,
                            'Expiration Date': expiration_date,
                            'Item Type': item_type,
                            'Notes': notes
                        }

                        if validate_new_row(new_item):
                            add_pantry_item(pd.Series(new_item))
                            st.success(f"'{item_name}' has been added to your pantry.")
                            st.session_state.show_add_form = False
                            st.rerun()
                        else:
                            st.error("Please complete all fields before adding the item.")

        # If the email is not confirmed
        elif is_user_authenticated() and not st.session_state.get('email_confirmed', False):
            st.warning("Your email address is not confirmed. Please confirm your email to access all features.")
            if st.button("Resend Activation Link", key='resend_activation_link_button'):
                resend_activation_link(st.session_state['user_id'])

    except Exception as e:
        logging.error(f"An error occurred in pantry_page: {str(e)}")
        st.error("An unexpected error occurred. Please try again later.")

def process_changes(original_df, edited_df):
    """
    Compare original and edited DataFrames and process additions, updates, and deletions.
    """
    original_ids = set(original_df['ID'])
    edited_ids = set(edited_df['ID'].dropna())

    # Identify deletions based on 'Delete' column
    deleted_ids = original_ids - edited_ids
    # Additionally, identify rows marked for deletion
    rows_marked_for_deletion = edited_df[edited_df['Delete'] == True]
    ids_marked_for_deletion = set(rows_marked_for_deletion['ID'])

    # Combine both deletion sets
    total_deleted_ids = deleted_ids | ids_marked_for_deletion

    # Identify additions
    added_rows = edited_df[edited_df['ID'].isnull()]

    # Identify updates
    common_ids = original_ids & edited_ids

    # Process deletions
    for id in total_deleted_ids:
        original_row = original_df[original_df['ID'] == id].iloc[0]
        delete_pantry_item(original_row)

    # Process updates
    for id in common_ids:
        original_row = original_df[original_df['ID'] == id].iloc[0]
        edited_row = edited_df[edited_df['ID'] == id].iloc[0]
        if not original_row.equals(edited_row):
            update_pantry_item(edited_row)

    # Process additions
    for _, row in added_rows.iterrows():
        if validate_new_row(row):
            add_pantry_item(row)
        else:
            st.warning("Please complete all required fields for the new item before adding.")

def validate_new_row(row):
    required_fields = ['Item Name', 'Quantity']
    for field in required_fields:
        if pd.isnull(row[field]) or row[field] == '':
            return False
    return True

def update_pantry_item(row):
    # Convert row to dictionary with native Python types
    updated_data = row.to_dict()

    # Prepare payload
    updated_data = {
        'item_name': updated_data['Item Name'],
        'quantity': int(updated_data['Quantity']),  # Ensure it's a native int
        'expiration_date': updated_data['Expiration Date'].isoformat() if pd.notnull(updated_data['Expiration Date']) else None,
        'item_type': updated_data['Item Type'],
        'notes': updated_data['Notes'],
    }
    item_id = row['ID']
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}

    # Serialize data to JSON
    data_json = json.dumps(updated_data)

    try:
        response = api_call_with_refresh(
            url=f'{os.getenv("DJANGO_URL")}/meals/api/pantry-items/{item_id}/',
            method='put',
            headers=headers,
            data=data_json
        )

        if response is None:
            logging.error("Failed to update pantry item due to authentication issues.")
            st.error("Failed to update pantry item. Please try logging in again.")
            return

        if response.status_code == 200:
            logging.info(f"Pantry item '{updated_data['item_name']}' updated successfully.")
        else:
            st.error(f"Failed to update pantry item: {response.json()}")
            logging.error(f"Failed to update pantry item: {response.json()}")

    except Exception as e:
        logging.error(f"Error updating pantry item: {e}")
        st.error("An error occurred while updating the pantry item. Please try again.")

def delete_pantry_item(row):
    item_id = row['ID']
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}

    try:
        response = api_call_with_refresh(
            url=f'{os.getenv("DJANGO_URL")}/meals/api/pantry-items/{item_id}/',
            method='delete',
            headers=headers,
            data=None
        )
        if response is None:
            logging.error("Failed to delete pantry item due to authentication issues.")
            st.error("Failed to delete pantry item. Please try logging in again.")
            return

        if response.status_code == 204:
            logging.info(f"Pantry item '{row['Item Name']}' deleted successfully.")
            # Remove the deleted row from the DataFrame
            st.session_state['edited_pantry_df'] = st.session_state['edited_pantry_df'][st.session_state['edited_pantry_df']['ID'] != item_id]
            st.rerun() 
        else:
            st.error(f"Failed to delete pantry item: {response.json()}")
            logging.error(f"Failed to delete pantry item: {response.json()}")

    except Exception as e:
        logging.error(f"Error deleting pantry item: {e}")
        st.error("An error occurred while deleting the pantry item. Please try again.")

def add_pantry_item(row):
    """
    Add a new pantry item.
    """
    # Prepare payload
    item_data = {
        'item_name': row['Item Name'],
        'quantity': int(row['Quantity']),
        'expiration_date': row['Expiration Date'].isoformat() if pd.notnull(row['Expiration Date']) else None,
        'item_type': row['Item Type'] if pd.notnull(row['Item Type']) else '',
        'notes': row['Notes'] if pd.notnull(row['Notes']) else '',
    }

    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}

    # Serialize data to JSON
    data_json = json.dumps(item_data)

    try:
        response = api_call_with_refresh(
            url=f'{os.getenv("DJANGO_URL")}/meals/api/pantry-items/',
            method='post',
            headers=headers,
            data=data_json
        )

        if response is None:
            logging.error("Failed to add pantry item due to authentication issues.")
            st.error("Failed to add pantry item. Please try logging in again.")
            return

        if response.status_code == 201:
            logging.info(f"Pantry item '{row['Item Name']}' added successfully.")
        else:
            st.error(f"Failed to add pantry item: {response.json()}")
            logging.error(f"Failed to add pantry item: {response.json()}")

    except Exception as e:
        logging.error(f"Error adding pantry item: {e}")
        st.error("An error occurred while adding the pantry item. Please try again.")

if __name__ == "__main__":
    pantry_page()
