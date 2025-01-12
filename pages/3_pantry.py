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

    # Logout button
    if 'is_logged_in' in st.session_state and st.session_state['is_logged_in']:
        if st.button("Logout", key='pantry_logout'):
            # Clear relevant session keys
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.success("Logged out successfully!")
            st.rerun()
        toggle_chef_mode()

    try:
        if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
            login_form()

        if is_user_authenticated() and st.session_state.get('email_confirmed', False):
            if 'current_role' in st.session_state and st.session_state['current_role'] != 'chef':
                st.title("Your Pantry")
                st.markdown("""
                ### Welcome to Your Pantry
                Keep track of your pantry items to minimize waste and maximize value. The **sautAI Pantry** helps you:

                - **Track Items**: Add items to your pantry and monitor their quantities and expiration dates.
                - **Reduce Waste**: Receive alerts for items approaching their expiration date, so you can use them before they go bad.
                - **Plan Meals Efficiently**: Enjoy meal recommendations tailored to use your pantry items before they expire.
                - **Stay Organized**: Easily manage your stock of canned and dry goods, along with custom notes for each item.
                
                By keeping your pantry updated, sautAI helps to align your meal plans with what you already have on hand, saving time and reducing food waste.
                
                **Editing Tags:** Enter tags as a comma-separated list. For example: `Gluten-Free, High-Protein`.
                """)

            # Initialize pagination
            if 'pantry_page_number' not in st.session_state:
                st.session_state.pantry_page_number = 1

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
                    # Build each row with the fields you want to display/edit
                    pantry_records.append({
                        'ID': int(item['id']),
                        'Item Name': item['item_name'],
                        'Quantity': item['quantity'],
                        'Weight Per Unit': item.get('weight_per_unit', None),
                        'Weight Unit': item.get('weight_unit', ''),
                        'Expiration Date': parse_expiration_date(item['expiration_date']),
                        'Item Type': item['item_type'],
                        'Notes': item['notes'],
                        'Tags': ', '.join(item.get('tags', [])),
                    })

                if not pantry_records:
                    st.info("No pantry items found.")
                else:
                    pantry_df = pd.DataFrame(pantry_records)
                    pantry_df['Delete'] = False

                    # Store original for comparison later
                    st.session_state['original_pantry_df'] = pantry_df.copy()

                    # Hide the ID column from display
                    display_df = pantry_df.drop(columns=['ID'])

                    # Show data_editor with custom columns
                    edited_df = st.data_editor(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            'Quantity': st.column_config.NumberColumn(
                                'Quantity',
                                min_value=0,
                                step=1
                            ),
                            'Weight Per Unit': st.column_config.NumberColumn(
                                'Weight Per Unit',
                                help="How many ounces or grams per can/bag?"
                            ),
                            'Weight Unit': st.column_config.SelectboxColumn(
                                'Weight Unit',
                                options=["", "oz", "lb", "g", "kg"],
                                help="The unit for weight_per_unit"
                            ),
                            'Expiration Date': st.column_config.DateColumn('Expiration Date'),
                            'Item Type': st.column_config.SelectboxColumn(
                                'Item Type',
                                options=['Canned', 'Dry']
                            ),
                            'Notes': st.column_config.TextColumn('Notes'),
                            'Tags': st.column_config.TextColumn('Tags'),
                            'Delete': st.column_config.CheckboxColumn('Delete', default=False),
                        },
                        num_rows="dynamic",
                        key='pantry_data_editor',
                    )

                    st.session_state['edited_pantry_df'] = edited_df

                    # Buttons for submission & cancellation
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button('Submit Changes', key='submit_changes_button'):
                            process_changes(
                                original_df=st.session_state['original_pantry_df'],
                                edited_df=st.session_state['edited_pantry_df']
                            )
                            st.success("Changes submitted successfully!")
                            st.rerun()
                    with col2:
                        if st.button('Cancel Changes', key='cancel_changes_button'):
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
                logging.error(f"Status code: {response.status_code}, Response: {response.text}")
            else:
                st.error("Error fetching pantry items.")
                if response:
                    logging.error(f"Status code: {response.status_code}, Response: {response.text}")
                else:
                    logging.error("No response from server.")

            # Add New Pantry Item form
            if not pantry_items or st.button("Add New Pantry Item", key='show_add_pantry_item_form'):
                st.session_state.show_add_form = True
            UNIT_OPTIONS = ['oz', 'lb', 'g', 'kg']

            if st.session_state.show_add_form:
                with st.form(key='add_pantry_item_form'):
                    item_name = st.text_input("Item Name")
                    quantity = st.number_input("Quantity", min_value=1, value=1, step=1)
                    weight_val = st.number_input("Weight Per Unit", min_value=0.0, value=0.0, step=0.1)
                    selected_unit = st.selectbox("Weight Unit", options=[""] + UNIT_OPTIONS, index=0, help="(Leave blank if not applicable)")
                    expiration_date = st.date_input("Expiration Date", value=date.today())
                    item_type = st.selectbox("Item Type", options=['Canned', 'Dry'])
                    notes = st.text_area("Notes")
                    tags_str = st.text_input("Tags (comma-separated)")
                    add_item_submit = st.form_submit_button("Add Item")

                    if add_item_submit:
                        new_item = {
                            'Item Name': item_name,
                            'Quantity': quantity,
                            'Weight Per Unit': weight_val,
                            'Weight Unit': None if selected_unit == "" else selected_unit,
                            'Expiration Date': expiration_date,
                            'Item Type': item_type,
                            'Notes': notes,
                            'Tags': tags_str,
                        }
                        if validate_new_row(new_item):
                            add_pantry_item(pd.Series(new_item))
                            st.success(f"'{item_name}' has been added to your pantry.")
                            st.session_state.show_add_form = False
                            st.rerun()
                        else:
                            st.error("Please complete all fields before adding the item.")

        elif is_user_authenticated() and not st.session_state.get('email_confirmed', False):
            st.warning("Your email address is not confirmed. Please confirm your email to access all features.")
            if st.button("Resend Activation Link", key='resend_activation_link_button'):
                resend_activation_link(st.session_state['user_id'])

    except Exception as e:
        logging.error(f"An error occurred in pantry_page: {str(e)}")
        st.error("An unexpected error occurred. Please try again later.")

def process_changes(original_df, edited_df):
    """
    Merge 'ID' from original_df onto edited_df by matching row index,
    then handle updates & deletions.

    original_df:  columns ['ID', 'Item Name', ..., 'Delete']
    edited_df:    columns ['Item Name', ..., 'Delete'] (missing ID)
    """
    # 1) Reattach ID
    merged_df = edited_df.copy()
    merged_df['ID'] = original_df['ID'].astype(int).values  # ensure int, not float
    
    # 2) Find items with Delete == True
    rows_for_deletion = merged_df[merged_df['Delete'] == True]
    delete_ids = set(rows_for_deletion['ID'])
    
    # 3) For updates
    for idx in merged_df.index:
        if merged_df.at[idx, 'Delete'] is True:
            # skip deleting here, handle after
            continue
        
        row_id = merged_df.at[idx, 'ID']
        # Check if row_id is in original_df
        original_rows = original_df[original_df['ID'] == row_id]
        if original_rows.empty:
            # No match in original, skip or log an error
            logging.warning(f"Row with ID={row_id} not found in original for update. Skipping.")
            continue
        
        original_row = original_rows.iloc[0]
        edited_row = merged_df.loc[idx]

        # Drop the ID/Delete columns for comparison
        original_comp = original_row.drop(['ID','Delete'], errors='ignore')
        edited_comp = edited_row.drop(['ID','Delete'], errors='ignore')
        
        if not original_comp.equals(edited_comp):
            # Something changed
            update_pantry_item(edited_row)
    
    # 4) Now do the deletions
    for row_id in delete_ids:
        # Retrieve from original df
        orig_rows = original_df[original_df['ID'] == row_id]
        if orig_rows.empty:
            logging.warning(f"Row with ID={row_id} not found in original for deletion. Possibly already deleted.")
            continue
        
        original_row = orig_rows.iloc[0]
        delete_pantry_item(original_row)

def validate_new_row(row):
    required_fields = ['Item Name', 'Quantity']
    for field in required_fields:
        if pd.isnull(row[field]) or row[field] == '':
            return False
    return True

def update_pantry_item(row):
    updated_data = row.to_dict()
    tags_str = updated_data['Tags'] if 'Tags' in updated_data else ''
    tags_list = [tag.strip() for tag in tags_str.split(',') if tag.strip()]

    # Build the payload
    payload = {
        'item_name': updated_data['Item Name'],
        'quantity': int(updated_data['Quantity']),
        'expiration_date': updated_data['Expiration Date'].isoformat() if pd.notnull(updated_data['Expiration Date']) else None,
        'item_type': updated_data['Item Type'],
        'notes': updated_data['Notes'] if pd.notnull(updated_data['Notes']) else '',
        'tags': tags_list
    }
    if 'Weight Per Unit' in updated_data and not pd.isnull(updated_data['Weight Per Unit']):
        payload['weight_per_unit'] = float(updated_data['Weight Per Unit'])
    if 'Weight Unit' in updated_data and updated_data['Weight Unit']:
        payload['weight_unit'] = updated_data['Weight Unit']

    item_id = updated_data['ID']
    data_json = json.dumps(payload)
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}

    try:
        resp = api_call_with_refresh(
            url=f'{os.getenv("DJANGO_URL")}/meals/api/pantry-items/{item_id}/',
            method='put',
            headers=headers,
            data=data_json
        )
        if resp is None:
            st.error("Failed to update pantry item. Please log in again.")
            return
        if resp.status_code == 200:
            logging.info(f"Updated pantry item '{payload['item_name']}' successfully.")
        else:
            st.error(f"Failed to update item: {resp.json()}")
            logging.error(f"Failed to update item: {resp.json()}")
    except Exception as e:
        logging.error(f"Error updating pantry item: {e}")
        st.error("An error occurred while updating the pantry item. Please try again.")

def delete_pantry_item(row):
    item_id = row['ID']
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}

    try:
        resp = api_call_with_refresh(
            url=f'{os.getenv("DJANGO_URL")}/meals/api/pantry-items/{item_id}/',
            method='delete',
            headers=headers
        )
        if resp is None:
            st.error("Failed to delete pantry item. Please log in again.")
            return
        if resp.status_code == 204:
            logging.info(f"Deleted pantry item '{row['Item Name']}' successfully.")
            st.success(f"Deleted '{row['Item Name']}'")
        else:
            st.error(f"Failed to delete item: {resp.json()}")
            logging.error(f"Failed to delete item: {resp.json()}")
    except Exception as e:
        logging.error(f"Error deleting pantry item: {e}")
        st.error("An error occurred while deleting the pantry item. Please try again.")

    # If successful
    st.success(f"Deleted '{row['Item Name']}'")
    logging.info(f"Deleted item ID={item_id} successfully.")

def add_pantry_item(row):
    tags_str = row.get('Tags', '')
    tags_list = [tag.strip() for tag in tags_str.split(',') if tag.strip()]

    payload = {
        'item_name': row['Item Name'],
        'quantity': int(row['Quantity']),
        'expiration_date': row['Expiration Date'].isoformat() if pd.notnull(row['Expiration Date']) else None,
        'item_type': row['Item Type'] if pd.notnull(row['Item Type']) else '',
        'notes': row['Notes'] if pd.notnull(row['Notes']) else '',
        'tags': tags_list
    }
    if 'Weight Per Unit' in row and not pd.isnull(row['Weight Per Unit']):
        payload['weight_per_unit'] = float(row['Weight Per Unit'])
    WEIGHT_UNIT_FIELD = 'Weight Unit'  # how your DataFrame references it
    if WEIGHT_UNIT_FIELD in row and row[WEIGHT_UNIT_FIELD]:
        payload['weight_unit'] = row[WEIGHT_UNIT_FIELD]

    
    data_json = json.dumps(payload)
    headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}

    try:
        resp = api_call_with_refresh(
            url=f'{os.getenv("DJANGO_URL")}/meals/api/pantry-items/',
            method='post',
            headers=headers,
            data=data_json
        )
        if resp is None:
            st.error("Failed to add pantry item. Please log in again.")
            return
        if resp.status_code == 201:
            logging.info(f"Pantry item '{row['Item Name']}' added successfully.")
        else:
            st.error(f"Failed to add item: {resp.json()}")
            logging.error(f"Failed to add item: {resp.json()}")
    except Exception as e:
        logging.error(f"Error adding pantry item: {e}")
        st.error("An error occurred while adding the pantry item. Please try again.")

if __name__ == "__main__":
    pantry_page()