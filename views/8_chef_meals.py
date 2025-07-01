import streamlit as st
import pandas as pd
import requests
import os
import json
import time
import traceback
import datetime
import logging
from datetime import datetime, timedelta
from dateutil.parser import parse
from utils import api_call_with_refresh, login_form, toggle_chef_mode, is_user_authenticated, validate_input, footer, safe_get_nested, safe_get, handle_api_errors

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("error.log"),
    logging.StreamHandler()
])

# Function to check chef status
def check_chef_status():
    """
    Check if the current user is a chef or has a pending request
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/chefs/api/chefs/check-chef-status/",
            method='get',
            headers=headers
        )
        if response and response.status_code == 200:
            return response.json()

    except Exception as e:
        st.error(f"Error checking chef status: {str(e)}")
        logging.error(f"Error checking chef status: {str(e)}")
        logging.error(traceback.format_exc())
        return {'is_chef': False, 'has_pending_request': False}

# Function to submit chef request
def submit_chef_request(data):
    """
    Submit a new chef request or update an existing one
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/chefs/api/chefs/submit-chef-request/",
            method='post',
            headers=headers,
            data=data
        )
        
        if response and response.status_code in [200, 201]:
            return response.json()
        else:
            if response:
                error_message = response.json().get('error', 'Failed to submit chef request')
                st.error(error_message)
            else:
                st.error("Failed to submit chef request")
            return None
    except Exception as e:
        st.error(f"Error submitting chef request: {str(e)}")
        logging.error(f"Error submitting chef request: {str(e)}")
        logging.error(traceback.format_exc())
        return None

# Function to display chef request form
def display_chef_request_form():
    """
    Display and handle the chef request submission form
    """
    st.title("Submit Chef Request")
    
    with st.form("chef_request_form"):
        experience = st.text_area("Culinary Experience", 
                                placeholder="Tell us about your cooking experience...")
        
        bio = st.text_area("Bio", 
                          placeholder="Tell us about yourself and your cooking style...")
        
        profile_pic = st.file_uploader("Profile Picture", 
                                     type=['jpg', 'jpeg', 'png'],
                                     help="Upload a professional photo of yourself")
        
        postal_codes = st.text_input("Serving Postal Codes", 
                                   placeholder="Enter postal codes separated by commas",
                                   help="Enter the postal codes you plan to serve")
        
        submit_button = st.form_submit_button("Submit Request")
    
    if submit_button:
        # Prepare the data
        data = {
            'experience': experience,
            'bio': bio,
            'postal_codes': [code.strip() for code in postal_codes.split(',') if code.strip()]
        }
        
        # Handle profile picture if uploaded
        if profile_pic:
            files = {'profile_pic': profile_pic}
        else:
            files = None
        
        # Submit the request
        result = submit_chef_request(data)
        
        if result:
            st.success("Chef request submitted successfully!")
            st.info("Please wait for approval from our team. You'll be notified when your request is reviewed.")
            st.rerun()

# Function to format currency
def format_currency(amount):
    return f"${float(amount):.2f}"

# Function to format datetime
def format_datetime(dt_str):
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%b %d, %Y %I:%M %p")
    except:
        return dt_str

# Function to create a Stripe account for chefs
def create_stripe_account():
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        data = {
            'user_id': st.session_state.user_id
        }

        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/stripe-account-link/",
            method='post',
            data=data,
            headers=headers
        )

        if response and response.status_code == 200:
            data = response.json()

            return data.get('url')

    except Exception as e:
        st.error(f"Error creating Stripe account: {str(e)}")
        logging.error(f"Error creating Stripe account: {str(e)}")
        logging.error(traceback.format_exc())
        return None

# Function to check Stripe account status
def check_stripe_account_status():
    """
    Check Stripe account status with enhanced diagnostic information
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/stripe-account-status/",
            method='get',
            headers=headers
        )
        
        if response and response.status_code == 200:
            data = response.json()
            
            # NEW: Handle enhanced diagnostic information
            if data.get('needs_onboarding') and data.get('continue_onboarding_url'):
                # User needs to continue onboarding with fresh link
                logging.info("User needs to continue onboarding")
            
            # NEW: Check for specific blocking issues
            if data.get('diagnostic', {}).get('currently_due'):
                currently_due = data['diagnostic']['currently_due']
                if 'external_account' in currently_due:
                    # User specifically needs to add bank account
                    data['bank_account_required'] = True
                    logging.info("User needs to add bank account")
            
            return data
        else:
            logging.error(f"Failed to check Stripe account status. Status: {response.status_code if response else 'No response'}")
            st.error("Failed to check Stripe account status")
            return {'has_account': False}
    except Exception as e:
        st.error(f"Error checking Stripe account status: {str(e)}")
        logging.error(f"Error checking Stripe account status: {str(e)}")
        logging.error(traceback.format_exc())
        return {'has_account': False}

@handle_api_errors
def get_bank_account_guidance():
    """
    Get country-specific guidance for bank account setup
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/bank-account-guidance/",
            method='get',
            headers=headers
        )
        
        if response and response.status_code == 200:
            data = response.json()
            # Log the response structure for debugging
            logging.info(f"Bank account guidance response structure: {type(data)}")
            if isinstance(data, dict):
                logging.info(f"Response keys: {list(data.keys())}")
                # Log nested structure if it exists
                if 'guidance' in data and isinstance(data['guidance'], dict):
                    logging.info(f"Guidance nested keys: {list(data['guidance'].keys())}")
            return data
        else:
            logging.warning(f"Bank account guidance API returned status: {response.status_code if response else 'No response'}")
            if response:
                try:
                    error_data = response.json()
                    logging.warning(f"Error response: {error_data}")
                except:
                    logging.warning(f"Error response text: {response.text}")
        return None
    except Exception as e:
        logging.error(f"Error getting bank account guidance: {str(e)}")
        logging.error(traceback.format_exc())
        return None

def regenerate_stripe_account_link():
    """
    Generate fresh account link for users already in onboarding
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/regenerate-stripe-link/",
            method='post',
            headers=headers
        )
        
        if response and response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logging.error(f"Error regenerating account link: {str(e)}")
        return None

# Function to get chef dashboard stats
def get_chef_dashboard_stats():
    """
    Get the dashboard statistics for the chef from the backend.
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        url = f"{os.getenv('DJANGO_URL')}/meals/api/chef-dashboard-stats/"
        
        response = api_call_with_refresh(
            url=url,
            method='get',
            headers=headers
        )
        
        if response and response.status_code == 200:
            data = response.json()
            logging.info(f"Chef dashboard stats: {data}")
            return data
        else:
            st.error("Failed to fetch dashboard statistics")
            logging.error(f"Failed to fetch chef dashboard stats. Status: {response.status_code if response else 'No response'}")
            return {}
    except Exception as e:
        st.error(f"Error fetching dashboard statistics: {str(e)}")
        logging.error(f"Error fetching dashboard statistics: {str(e)}")
        logging.error(traceback.format_exc())
        return {}

# Function to fetch chef meal events
def fetch_chef_meal_events(my_events=False):
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        url = f"{os.getenv('DJANGO_URL')}/meals/api/chef-meal-events/"
        
        # Prepare parameters
        params = {}
        if my_events:
            params['my_events'] = 'true'
            
        logging.info(f"Fetching chef meal events from: {url} with params={params}")
        response = api_call_with_refresh(
            url=url,
            method='get',
            headers=headers,
            params=params
        )
        if response and response.status_code == 200:
            data = response.json()
            logging.info(f"Chef meal events API response type: {type(data)}")
            
            # Add more detailed logging to understand the structure
            if isinstance(data, dict):
                logging.info(f"API response is a dict with keys: {data.keys()}")
                if 'details' in data:
                    if isinstance(data['details'], dict):
                        logging.info(f"'details' is a dict with keys: {data['details'].keys()}")
                    else:
                        logging.info(f"'details' is not a dict, it's a {type(data['details'])}")
            
            # Handle nested dictionary response structure
            events_list = []
            if isinstance(data, list):
                events_list = data
                logging.info(f"Response is a list with {len(events_list)} events")
            elif isinstance(data, dict):
                # Check multiple possible response structures
                if 'results' in data:
                    events_list = data['results']
                    logging.info(f"Found events in 'results'. Count: {len(events_list)}")
                elif 'events' in data:
                    events_list = data['events']
                    logging.info(f"Found events in 'events'. Count: {len(events_list)}")
                elif 'details' in data:
                    if isinstance(data['details'], list):
                        events_list = data['details']
                        logging.info(f"Found events in 'details' list. Count: {len(events_list)}")
                    elif isinstance(data['details'], dict):
                        if 'results' in data['details']:
                            events_list = data['details']['results']
                            logging.info(f"Found events in details.results. Count: {len(events_list)}")
                        elif 'events' in data['details']:
                            events_list = data['details']['events']
                            logging.info(f"Found events in details.events. Count: {len(events_list)}")
                if not events_list:
                    # Last resort - see if the dict itself contains event data
                    if 'id' in data and 'event_date' in data and 'meal' in data:
                        events_list = [data]
                        logging.info("Response appears to be a single event - converted to list")
                
                if not events_list:
                    logging.error(f"Unexpected dictionary structure. Could not find events in: {data.keys()}")
                    logging.error(f"Full response data: {data}")
                    return []
            
            # Validate each event
            if events_list:
                logging.info(f"Events list length: {len(events_list)}")
                # Verify each event is a dictionary with required fields
                valid_events = []
                for event in events_list:
                    if isinstance(event, dict) and 'event_date' in event and 'meal' in event:
                        valid_events.append(event)
                    else:
                        logging.error(f"Invalid event format: {event}")
                
                if len(valid_events) != len(events_list):
                    logging.warning(f"Found {len(valid_events)} valid events out of {len(events_list)} total")
                
                return valid_events
            else:
                logging.info(f"No events found in the response for my_events={my_events}")
                return []
        else:
            logging.error(f"Failed to fetch chef meal events. Status: {response.status_code if response else 'No response'}")
            st.error("Failed to fetch chef meal events")
            return []
    except Exception as e:
        st.error(f"Error fetching chef meal events: {str(e)}")
        logging.error(f"Error fetching chef meal events: {str(e)}")
        logging.error(traceback.format_exc())
        return []

# Function to fetch chef meal orders
def fetch_chef_meal_orders(as_chef=False):
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        url = f"{os.getenv('DJANGO_URL')}/meals/api/chef-meal-orders/"
        
        # Add query parameter for chef view
        if as_chef:
            url += "?as_chef=true"
            
        logging.info(f"Fetching chef meal orders from: {url}")
        response = api_call_with_refresh(
            url=url,
            method='get',
            headers=headers
        )
        
        if response and response.status_code == 200:
            data = response.json()
            # Log a summary of the response
            if isinstance(data, list):
                logging.info(f"Orders list length: {len(data)}")
                if len(data) > 0:
                    logging.info(f"Sample order: {data[0]}")
            elif isinstance(data, dict):
                logging.info(f"Orders dict keys: {data.keys()}")
                if 'details' in data and isinstance(data['details'], dict):
                    logging.info(f"Details keys: {data['details'].keys()}")
                    if 'results' in data['details']:
                        results = data['details']['results']
                        logging.info(f"Results count: {len(results) if isinstance(results, list) else 'not a list'}")
                        if isinstance(results, list) and len(results) > 0:
                            logging.info(f"Sample result: {results[0]}")
            
            # Validate the response format
            if isinstance(data, list):
                logging.info(f"Orders list length: {len(data)}")
                if data and len(data) > 0:
                    logging.info(f"First order type: {type(data[0])}")
                    logging.info(f"First order keys: {data[0].keys() if isinstance(data[0], dict) else 'Not a dict'}")
            elif isinstance(data, dict):
                logging.info(f"Orders dict keys: {data.keys()}")
                
            return data
        else:
            st.error("Failed to fetch chef meal orders")
            logging.error(f"Failed to fetch chef meal orders. Status: {response.status_code if response else 'No response'}")
            if response:
                try:
                    logging.error(f"Response content: {response.text}")
                except:
                    pass
            return []
    except Exception as e:
        st.error(f"Error fetching chef meal orders: {str(e)}")
        logging.error(f"Error fetching chef meal orders: {str(e)}")
        logging.error(traceback.format_exc())
        return []

# Function to create a chef meal event
def create_chef_meal_event(data):
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/chef-meal-events/",
            method='post',
            headers=headers,
            data=data
        )
        
        if response and response.status_code in [200, 201]:
            return response.json()
        else:
            if response:
                try:
                    error_data = response.json()
                    # Format error messages for better display
                    if isinstance(error_data, dict):
                        # If we have detailed field errors, format them nicely
                        if any(isinstance(error_data.get(key), (list, dict)) for key in error_data):
                            error_message = "The following errors occurred:\n"
                            for field, errors in error_data.items():
                                if isinstance(errors, list):
                                    error_message += f"• {field.replace('_', ' ').title()}: {' '.join(errors)}\n"
                                elif isinstance(errors, dict):
                                    error_message += f"• {field.replace('_', ' ').title()}: {errors}\n"
                        else:
                            # General error message
                            error_message = error_data.get('error', 'Failed to create chef meal event')
                    else:
                        error_message = "Failed to create chef meal event with an unexpected response format."
                    
                    return {'error': error_message}
                except ValueError:
                    # If response is not JSON
                    return {'error': f"Failed to create chef meal event: {response.text}"}
            else:
                return {'error': "Failed to create chef meal event. No response from server."}
    except Exception as e:
        logging.error(f"Error creating chef meal event: {str(e)}")
        logging.error(traceback.format_exc())
        return {'error': f"Error creating chef meal event: {str(e)}"}

# Function to update a chef meal event
def update_chef_meal_event(event_id, data):
    """
    Update an existing chef meal event.
    
    Args:
        event_id: The ID of the event to update
        data: Dictionary containing event data to update
    
    Returns:
        Dictionary with the updated event data or error message
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/chef-meal-events/{event_id}/update/",
            method='put',
            headers=headers,
            data=data
        )
        
        if response and response.status_code == 200:
            result = response.json()
            if 'status' in result and result['status'] == 'success':
                return result.get('details', result)
            return result
        else:
            if response:
                try:
                    error_data = response.json()
                    # Format error messages for better display
                    if isinstance(error_data, dict):
                        if 'status' in error_data and error_data['status'] == 'error' and 'message' in error_data:
                            error_message = error_data['message']
                            
                            # Check for detailed field errors
                            if 'details' in error_data and isinstance(error_data['details'], dict):
                                field_errors = []
                                for field, errors in error_data['details'].items():
                                    if isinstance(errors, list):
                                        field_errors.append(f"{field}: {', '.join(errors)}")
                                    else:
                                        field_errors.append(f"{field}: {errors}")
                                
                                if field_errors:
                                    error_message += f"\n• " + "\n• ".join(field_errors)
                        else:
                            # Fallback for non-standard error format
                            error_message = error_data.get('error', 'Failed to update chef meal event')
                    else:
                        error_message = "Failed to update chef meal event with an unexpected response format."
                    
                    return {'error': error_message}
                except ValueError:
                    # If response is not JSON
                    return {'error': f"Failed to update chef meal event: {response.text}"}
            else:
                return {'error': "Failed to update chef meal event. No response from server."}
    except Exception as e:
        logging.error(f"Error updating chef meal event: {str(e)}")
        logging.error(traceback.format_exc())
        return {'error': f"Error updating chef meal event: {str(e)}"}

# Function to cancel a chef meal event
def cancel_chef_meal_event(event_id, reason):

    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/chef-meal-events/{event_id}/cancel/",
            method='post',
            headers=headers,
            data={'reason': reason}
        )
        
        if response and response.status_code == 200:

            return True
        else:
            st.error("Failed to cancel event")
            return False
    except Exception as e:
        st.error(f"Error cancelling chef meal event: {str(e)}")
        logging.error(f"Error cancelling chef meal event: {str(e)}")
        logging.error(traceback.format_exc())
        return False

# Function to place a chef meal order
def place_chef_meal_order(event_id, quantity, special_requests):
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        data = {
            'meal_event': event_id,
            'quantity': quantity,
            'special_requests': special_requests
        }
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/chef-meal-orders/",
            method='post',
            headers=headers,
            data=data
        )
        
        if response and response.status_code in [200, 201]:
            return response.json()
        else:
            if response:
                error_message = response.json().get('error', 'Failed to place order')
                st.error(error_message)
            else:
                st.error("Failed to place order")
            return None
    except Exception as e:
        st.error(f"Error placing chef meal order: {str(e)}")
        logging.error(f"Error placing chef meal order: {str(e)}")
        logging.error(traceback.format_exc())
        return None

# Function to cancel a chef meal order
def cancel_chef_meal_order(order_id, reason):
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/chef-meal-orders/{order_id}/cancel/",
            method='post',
            headers=headers,
            data={'reason': reason}
        )
        
        if response and response.status_code == 200:
            return True
        else:
            st.error("Failed to cancel order")
            return False
    except Exception as e:
        st.error(f"Error cancelling chef meal order: {str(e)}")
        logging.error(f"Error cancelling chef meal order: {str(e)}")
        logging.error(traceback.format_exc())
        return False

# Function to confirm a chef meal order
def confirm_chef_meal_order(order_id):
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/chef-meal-orders/{order_id}/confirm/",
            method='post',
            headers=headers
        )
        
        if response and response.status_code == 200:
            return True
        else:
            if response:
                error_message = response.json().get('error', 'Failed to confirm order')
                st.error(error_message)
            else:
                st.error("Failed to confirm order")
            return False
    except Exception as e:
        st.error(f"Error confirming chef meal order: {str(e)}")
        logging.error(f"Error confirming chef meal order: {str(e)}")
        logging.error(traceback.format_exc())
        return False

# Function to format dates in a more user-friendly way
def format_date(date_str):
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%A, %B %d, %Y')
    except:
        return date_str

# Function to fetch chef's meals
def fetch_chef_meals():
    """
    Fetch meals created by the chef.
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        url = f"{os.getenv('DJANGO_URL')}/meals/api/meals/"
        logging.info(f"Fetching chef meals from: {url}")
        
        response = api_call_with_refresh(
            url=url,
            method='get',
            headers=headers
        )
        
        if response and response.status_code == 200:
            data = response.json()
            
            # Extract meals from the response structure
            meals_list = []
            if isinstance(data, dict) and 'status' in data and data['status'] == 'success':
                if 'details' in data:
                    # Handle when details are directly a list or contain results
                    details = data['details']
                    if isinstance(details, list):
                        meals_list = details
                    elif isinstance(details, dict) and 'results' in details:
                        meals_list = details['results']
                    else:
                        meals_list = []
            elif isinstance(data, list):
                meals_list = data
            
            logging.info(f"Extracted {len(meals_list)} chef meals")
            return meals_list
        else:
            if response:
                logging.error(f"Error fetching chef meals: {response.status_code}, {response.text}")
            return []
    except Exception as e:
        logging.error(f"Error in fetch_chef_meals: {str(e)}", exc_info=True)
        return []

def create_chef_dish(data):
    """
    Create a new chef dish by calling the create-chef-dish API endpoint.
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/create-chef-dish/",
            method='post',
            headers=headers,
            data=data
        )
        

        if response and response.status_code in [200, 201]:
            logging.info(f"Dish creation successful: {response.json()}")
            return response.json()
        else:
            if response:
                logging.error(f"Dish creation failed: {response.status_code}, {response.text}")
                error_data = response.json()
                error_message = error_data.get('message', 'Failed to create dish')
                details = error_data.get('details', {})
                
                # Check if the details contain field errors
                if isinstance(details, dict) and details:
                    field_errors = []
                    for field, error_list in details.items():
                        if isinstance(error_list, list):
                            error_str = ', '.join(error_list)
                        else:
                            error_str = str(error_list)
                        field_errors.append(f"{field}: {error_str}")
                    
                    if field_errors:
                        error_message += f"\n• " + "\n• ".join(field_errors)
                
                st.error(error_message)
            else:
                st.error("Network error occurred while creating the dish")
            return None
    except Exception as e:
        logging.error(f"Error creating chef dish: {str(e)}")
        st.error(f"An error occurred: {str(e)}")
        return None

def fetch_chef_dishes():
    """
    Fetch dishes created by the chef.
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        url = f"{os.getenv('DJANGO_URL')}/meals/api/dishes/?chef_dishes=true"
        logging.info(f"Fetching chef dishes from: {url}")
        
        response = api_call_with_refresh(
            url=url,
            method='get',
            headers=headers
        )
        
        if response and response.status_code == 200:
            data = response.json()
            logging.info(f"Chef dishes API response: {data}")
            
            # Extract dishes from the standardized response structure
            dishes_list = []
            if isinstance(data, dict) and 'status' in data and data['status'] == 'success':
                if 'details' in data:
                    # Handle when details are directly a list or contain results
                    details = data['details']
                    if isinstance(details, list):
                        dishes_list = details
                    elif isinstance(details, dict) and 'results' in details:
                        dishes_list = details['results']
            elif isinstance(data, list):
                # In case the API returns a direct list
                dishes_list = data
            
            return dishes_list
        else:
            # Handle API errors
            if response:
                logging.error(f"Error fetching chef dishes: {response.status_code}, {response.text}")
                if response.status_code == 403:
                    st.warning("You don't have permission to access dishes. Make sure your chef account is set up correctly.")
            else:
                logging.error("No response received when fetching chef dishes")
            return []
    except Exception as e:
        logging.error(f"Error fetching chef dishes: {str(e)}")
        logging.error(traceback.format_exc())
        return []

def fetch_dietary_preferences():
    """
    Fetch dietary preferences from the backend or use a predefined list like in the profile page.
    """
    try:
        url = f"{os.getenv('DJANGO_URL')}/meals/api/dietary-preferences/"
        logging.info(f"Fetching dietary preferences from: {url}")
        
        response = api_call_with_refresh(
            url=url,
            method='get'
        )
        
        if response and response.status_code == 200:
            data = response.json()
            logging.info(f"Dietary preferences API response: {data}")
            
            # Extract preferences from the response structure
            prefs_list = []
            if isinstance(data, list):
                # Direct list of preferences
                prefs_list = data
            elif isinstance(data, dict):
                # Handle different response structures
                if 'details' in data and isinstance(data['details'], list):
                    prefs_list = data['details']
                elif 'status' in data and data['status'] == 'success' and 'details' in data:
                    prefs_list = data['details']
                elif 'results' in data:
                    prefs_list = data['results']
            
            # Convert preferences to the expected format if needed
            formatted_prefs = []
            for pref in prefs_list:
                if isinstance(pref, dict):
                    # Already in dict format, make sure it has id and name
                    if 'id' in pref and 'name' in pref:
                        formatted_prefs.append(pref)
                    elif 'name' in pref:
                        # Create an id from the name if missing
                        formatted_prefs.append({
                            'id': pref.get('id', pref['name']),
                            'name': pref['name']
                        })
                elif isinstance(pref, str):
                    # Convert string preferences to dict format
                    formatted_prefs.append({
                        'id': pref,
                        'name': pref
                    })
            
            return formatted_prefs
        else:
            if response:
                logging.error(f"Error fetching dietary preferences: {response.status_code}, {response.text}")
            return use_default_preferences()
    except Exception as e:
        logging.error(f"Error fetching dietary preferences: {str(e)}")
        return use_default_preferences()
    
def use_default_preferences():
    """
    Return the default list of dietary preferences as used in the profile page.
    """
    # Use the same list as in the profile page
    default_prefs = [
        'Everything', 'Vegetarian', 'Pescatarian', 'Gluten-Free', 'Keto', 
        'Paleo', 'Halal', 'Kosher', 'Low-Calorie', 'Low-Sodium', 'High-Protein', 
        'Dairy-Free', 'Nut-Free', 'Raw Food', 'Whole 30', 'Low-FODMAP', 
        'Diabetic-Friendly', 'Vegan'
    ]
    
    # Convert to the format expected by our function
    return [{'id': pref, 'name': pref} for pref in default_prefs]

def update_chef_dish(dish_id, data):
    """
    Update an existing chef dish by calling the update-chef-dish API endpoint.
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/dishes/{dish_id}/update/",
            method='put',
            headers=headers,
            data=data
        )
        
        if response and response.status_code in [200, 201]:
            logging.info(f"Dish update successful: {response.json()}")
            return response.json()
        else:
            if response:
                logging.error(f"Dish update failed: {response.status_code}, {response.text}")
                error_data = response.json()
                error_message = error_data.get('message', 'Failed to update dish')
                st.error(error_message)
            else:
                st.error("Network error occurred while updating the dish")
            return None
    except Exception as e:
        logging.error(f"Error updating chef dish: {str(e)}")
        st.error(f"An error occurred: {str(e)}")
        return None

def delete_chef_dish(dish_id):
    """
    Delete a chef dish by calling the delete-chef-dish API endpoint.
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/dishes/{dish_id}/delete/",
            method='delete',
            headers=headers
        )
        
        if response and response.status_code == 200:
            logging.info(f"Dish deletion successful: {response.json()}")
            return response.json()
        else:
            if response:
                logging.error(f"Dish deletion failed: {response.status_code}, {response.text}")
                error_data = response.json()
                error_message = error_data.get('message', 'Failed to delete dish')
                st.error(error_message)
            else:
                st.error("Network error occurred while deleting the dish")
            return None
    except Exception as e:
        logging.error(f"Error deleting chef dish: {str(e)}")
        st.error(f"An error occurred: {str(e)}")
        return None

# Functions for managing ingredients
def fetch_chef_ingredients():
    """
    Fetch ingredients created by the chef.
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        url = f"{os.getenv('DJANGO_URL')}/meals/api/ingredients/?chef_ingredients=true"
        logging.info(f"Fetching chef ingredients from: {url}")
        
        response = api_call_with_refresh(
            url=url,
            method='get',
            headers=headers
        )
        
        if response and response.status_code == 200:
            data = response.json()
            logging.info(f"Chef ingredients API response: {data}")
            
            # Extract ingredients from the standardized response structure
            ingredients_list = []
            if isinstance(data, dict) and 'status' in data and data['status'] == 'success':
                if 'details' in data:
                    # Handle when details are directly a list or contain results
                    details = data['details']
                    if isinstance(details, list):
                        ingredients_list = details
                    elif isinstance(details, dict) and 'results' in details:
                        ingredients_list = details['results']
            elif isinstance(data, list):
                # In case the API returns a direct list
                ingredients_list = data
            
            return ingredients_list
        else:
            # Handle API errors
            if response:
                logging.error(f"Error fetching chef ingredients: {response.status_code}, {response.text}")
                if response.status_code == 403:
                    st.warning("You don't have permission to access ingredients. Make sure your chef account is set up correctly.")
            else:
                logging.error("No response received when fetching chef ingredients")
            return []
    except Exception as e:
        logging.error(f"Error fetching chef ingredients: {str(e)}")
        logging.error(traceback.format_exc())
        return []

def create_chef_ingredient(data):
    """
    Create a new chef ingredient by calling the create-chef-ingredient API endpoint.
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/chef/ingredients/",
            method='post',
            headers=headers,
            data=data
        )
        
        if response and response.status_code in [200, 201]:
            logging.info(f"Ingredient creation successful: {response.json()}")
            return response.json()
        else:
            if response:
                logging.error(f"Ingredient creation failed: {response.status_code}, {response.text}")
                error_data = response.json()
                error_message = error_data.get('message', 'Failed to create ingredient')
                details = error_data.get('details', {})
                
                # Check if the details contain field errors
                if isinstance(details, dict) and details:
                    field_errors = []
                    for field, error_list in details.items():
                        if isinstance(error_list, list):
                            error_str = ', '.join(error_list)
                        else:
                            error_str = str(error_list)
                        field_errors.append(f"{field}: {error_str}")
                    
                    if field_errors:
                        error_message += f"\n• " + "\n• ".join(field_errors)
                
                st.error(error_message)
            else:
                st.error("Network error occurred while creating the ingredient")
            return None
    except Exception as e:
        logging.error(f"Error creating chef ingredient: {str(e)}")
        st.error(f"An error occurred: {str(e)}")
        return None

def update_chef_ingredient(ingredient_id, data):
    """
    Update an existing chef ingredient by calling the update API endpoint.
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/chef/ingredients/{ingredient_id}/",
            method='put',
            headers=headers,
            data=data
        )
        
        if response and response.status_code in [200, 201]:
            logging.info(f"Ingredient update successful: {response.json()}")
            return response.json()
        else:
            if response:
                logging.error(f"Ingredient update failed: {response.status_code}, {response.text}")
                error_data = response.json()
                error_message = error_data.get('message', 'Failed to update ingredient')
                st.error(error_message)
            else:
                st.error("Network error occurred while updating the ingredient")
            return None
    except Exception as e:
        logging.error(f"Error updating chef ingredient: {str(e)}")
        st.error(f"An error occurred: {str(e)}")
        return None

def delete_chef_ingredient(ingredient_id):
    """
    Delete a chef ingredient by calling the delete API endpoint.
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/chef/ingredients/{ingredient_id}/delete/",
            method='delete',
            headers=headers
        )
        
        if response and response.status_code == 200:
            logging.info(f"Ingredient deletion successful: {response.json()}")
            return response.json()
        else:
            if response:
                logging.error(f"Ingredient deletion failed: {response.status_code}, {response.text}")
                error_data = response.json()
                error_message = error_data.get('message', 'Failed to delete ingredient')
                st.error(error_message)
            else:
                st.error("Network error occurred while deleting the ingredient")
            return None
    except Exception as e:
        logging.error(f"Error deleting chef ingredient: {str(e)}")
        st.error(f"An error occurred: {str(e)}")
        return None

# Main function for chef meals page
def chef_meals():
    # Check if user is logged in
    if 'is_logged_in' not in st.session_state or not st.session_state['is_logged_in']:
        logging.info("User not logged in")
        login_form()
        st.stop()
    else:
        logging.info("User logged in, username: %s", st.session_state.get('username', 'unknown'))
    
    # Check chef status
    chef_status = check_chef_status()
    if not chef_status['is_chef']:
        st.warning("This page is only accessible to authorized chefs.")
        st.info("Interested in becoming a chef? Visit your profile page to submit an application.")
        st.stop()
    else:
        logging.info("Access granted - user is a chef")

    # Title and description
    st.title("Chef Meal Management")
    st.write("Create and manage your chef meal events and track orders from customers.")
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Dashboard", "My Meal Events", "Received Orders", "Manage Meals", "Create Event"])
    
    # Tab 1: Chef Dashboard
    with tab1:
        st.header("Chef Dashboard")
        
        # Check Stripe account status
        stripe_status = check_stripe_account_status()



        if not stripe_status.get('has_account', False):
            st.warning("You need to set up your Stripe account to receive payments for your meal events.")
            if st.button("Set Up Stripe Account"):
                stripe_url = create_stripe_account()
                if stripe_url:
                    st.success("Stripe account creation initiated. Click the link below to continue:")
                    st.markdown(f"[Complete Stripe Onboarding]({stripe_url})")
                    st.info("After completing the onboarding, return to this page.")
        elif not stripe_status.get('is_active', False):
            # NEW: Enhanced messaging based on diagnostic info
            diagnostic = stripe_status.get('diagnostic', {})
            currently_due = diagnostic.get('currently_due', [])
            
            if 'external_account' in currently_due:
                # Specific bank account issue
                st.warning("⚠️ Your Stripe account needs a bank account to receive payments.")
                
                # Get country-specific guidance
                guidance = get_bank_account_guidance()
                if guidance and not safe_get(guidance, 'financial_connections_available', True):
                    # Show guidance for non-US users using safe access
                    default_message = 'Bank account setup guidance is available for your region.'
                    
                    # Try to get message from nested structure first, then fallback to root level
                    message = safe_get_nested(guidance, ['guidance', 'message'], 
                                            safe_get(guidance, 'message', default_message))
                    st.info("🌍 " + message)
                    
                    # Try to get steps from nested structure first, then fallback to root level
                    steps = safe_get_nested(guidance, ['guidance', 'steps'], 
                                          safe_get(guidance, 'steps', []))
                    
                    if steps:
                        with st.expander("How to add your bank account manually"):
                            if isinstance(steps, list):
                                for step in steps:
                                    st.write(f"• {str(step)}")
                            else:
                                # Handle case where steps is not a list
                                st.write(f"• {str(steps)}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Continue Bank Account Setup"):
                        if stripe_status.get('continue_onboarding_url'):
                            st.markdown(f"[Continue Setup]({stripe_status['continue_onboarding_url']})")
                        else:
                            # Generate fresh link
                            fresh_link = regenerate_stripe_account_link()
                            if fresh_link and fresh_link.get('onboarding_url'):
                                st.markdown(f"[Continue Setup]({fresh_link['onboarding_url']})")
                
                with col2:
                    if st.button("Get Fresh Setup Link"):
                        fresh_link = regenerate_stripe_account_link()
                        if fresh_link and fresh_link.get('onboarding_url'):
                            st.success("New setup link generated!")
                            st.markdown(f"[Complete Setup]({fresh_link['onboarding_url']})")
            else:
                # General onboarding incomplete
                st.warning("Your Stripe account setup is incomplete.")
                missing_items = diagnostic.get('currently_due', [])
                if missing_items:
                    st.write("Missing requirements:")
                    for item in missing_items:
                        st.write(f"• {item.replace('_', ' ').title()}")
                
                if st.button("Complete Setup"):
                    if stripe_status.get('continue_onboarding_url'):
                        st.markdown(f"[Complete Setup]({stripe_status['continue_onboarding_url']})")
        elif stripe_status.get('disabled_reason', None):
            st.warning(f"There's an issue with your Stripe account: {stripe_status.get('disabled_reason', 'Unknown reason')}")
            if st.button("Update Stripe Account"):
                stripe_url = create_stripe_account()
                if stripe_url:
                    st.success("Click the link below to update your Stripe account:")
                    st.markdown(f"[Update Stripe Account]({stripe_url})")
        else:
            st.success("✅ Your Stripe account is active and ready!")
            
            # NEW: Show account health info
            diagnostic = stripe_status.get('diagnostic', {})
            if diagnostic.get('external_accounts_count', 0) > 0:
                st.info(f"💳 {diagnostic['external_accounts_count']} bank account(s) connected")
        
        # Display dashboard statistics
        stats = get_chef_dashboard_stats()
        
        if stats:
            # Top row metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Upcoming Events", stats.get('upcoming_events_count', 0))
            
            with col2:
                st.metric("Active Orders", stats.get('active_orders_count', 0))
            
            with col3:
                st.metric("Past Events", stats.get('past_events_count', 0))
            
            with col4:
                st.metric("Average Rating", f"{float(stats.get('avg_rating', 0)):.1f}★")
            
            # Revenue section
            st.subheader("Revenue")
            
            rev_col1, rev_col2, rev_col3 = st.columns(3)
            
            with rev_col1:
                st.metric("Monthly Revenue", format_currency(float(stats.get('revenue_this_month', 0))))
            
            with rev_col2:
                st.metric("Monthly Refunds", format_currency(float(stats.get('refunds_this_month', 0))))
            
            with rev_col3:
                st.metric("Net Revenue", format_currency(float(stats.get('net_revenue', 0))))
            
            # Additional metrics
            st.subheader("Additional Metrics")
            
            add_col1, add_col2, add_col3 = st.columns(3)
            
            with add_col1:
                st.metric("Customer Savings", format_currency(float(stats.get('customer_savings', 0))),
                          help="Amount saved by customers through dynamic pricing")
            
            with add_col2:
                st.metric("Pending Adjustments", stats.get('pending_price_adjustments', 0),
                          help="Number of orders with pending price adjustments")
            
            with add_col3:
                st.metric("Reviews", stats.get('review_count', 0))
            
            # Order History section
            st.subheader("Order History")
            # Fetch received orders for analytics
            orders = fetch_chef_meal_orders(as_chef=True)
            # Display Active Orders Summary Card
            st.subheader("Active Orders Summary")
            try:
                # Process the orders data to extract active orders
                active_events = []
                active_orders = []
                total_revenue = 0.0
                
                if isinstance(orders, list):
                    # Process list of orders directly
                    for order in orders:
                        active_orders.append(order)
                        # Calculate revenue from meals_for_chef
                        if 'meals_for_chef' in order:
                            for meal in order['meals_for_chef']:
                                price = float(meal.get('price', 0))
                                quantity = int(meal.get('quantity', 1))
                                total_revenue += price * quantity
                        elif 'total_value_for_chef' in order:
                            total_revenue += float(order['total_value_for_chef'])
                
                elif isinstance(orders, dict) and 'details' in orders and 'results' in orders['details']:

                    # Simply add any event that has active_orders to our list
                    for event in orders['details']['results']:
                        if 'active_orders' in event and event['active_orders']:

                            active_events.append(event)
                            for order in event['active_orders']:
                                active_orders.append(order)
                                # Calculate revenue
                                if 'price_paid' in order and 'quantity' in order:
                                    price = float(order['price_paid'])
                                    quantity = int(order.get('quantity', 1))
                                    total_revenue += price * quantity
                
                # Display order summaries
                if active_orders:
                    # Show counts by status
                    status_counts = {}
                    meal_counts = {}
                    customer_counts = {}
                    total_items = 0
                    
                    for order in active_orders:
                        status = order.get('status', 'unknown').lower()
                        status_counts[status] = status_counts.get(status, 0) + 1
                        
                        # Track unique customers
                        customer = order.get('customer_username', 'unknown')
                        customer_counts[customer] = customer_counts.get(customer, 0) + 1
                        
                        # Track total items across all orders
                        if 'meals_for_chef' in order:
                            for meal in order['meals_for_chef']:
                                meal_name = meal.get('meal_name', 'unknown')
                                quantity = int(meal.get('quantity', 1))
                                meal_counts[meal_name] = meal_counts.get(meal_name, 0) + quantity
                                total_items += quantity
                    
                    # Create metrics for different order statuses
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Orders", len(active_orders))
                    with col2:
                        st.metric("Total Revenue", format_currency(total_revenue))
                    with col3:
                        st.metric("Total Items", total_items)
                    
                    # Second row of metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Placed Orders", status_counts.get('placed', 0))
                    with col2:
                        st.metric("Confirmed Orders", status_counts.get('confirmed', 0))
                    with col3:
                        st.metric("Unique Customers", len(customer_counts))
                    
                    # Display popular items
                    if meal_counts:
                        st.subheader("Popular Items")
                        # Convert meal counts to dataframe for display
                        meal_data = []
                        for meal, count in meal_counts.items():
                            meal_data.append({"Meal": meal, "Orders": count})
                        
                        meal_df = pd.DataFrame(meal_data)
                        if not meal_df.empty:
                            meal_df = meal_df.sort_values(by="Orders", ascending=False)
                            st.bar_chart(meal_df.set_index("Meal"))
                    
                    # Display active orders in an expander
                    with st.expander("View Active Orders", expanded=True):
                        # Create dataframe for all orders
                        orders_df_data = []
                        for order in active_orders:
                            order_items = []
                            total_quantity = 0
                            if 'meals_for_chef' in order:
                                for meal in order['meals_for_chef']:
                                    meal_name = meal.get('meal_name', 'unknown')
                                    quantity = int(meal.get('quantity', 1))
                                    order_items.append(f"{meal_name} (x{quantity})")
                                    total_quantity += quantity
                            
                            orders_df_data.append({
                                'Order ID': order.get('id', 'N/A'),
                                'Customer': order.get('customer_username', 'Unknown'),
                                'Status': order.get('status', 'unknown').upper(),
                                'Items': ", ".join(order_items),
                                'Total Quantity': total_quantity,
                                'Total Value': format_currency(float(order.get('total_value_for_chef', 0))),
                                'Order Date': format_datetime(order.get('order_date', '')),
                                'Updated': format_datetime(order.get('updated_at', ''))
                            })
                        
                        orders_df = pd.DataFrame(orders_df_data)
                        if not orders_df.empty:
                            st.dataframe(orders_df, use_container_width=True)
                        
                        # Show individual order details
                        for order in active_orders:
                            with st.container():
                                st.markdown(f"### Order #{order.get('id', 'N/A')} - {order.get('status', 'unknown').upper()}")
                                
                                col1, col2 = st.columns([3, 2])
                                with col1:
                                    st.markdown(f"**Customer:** {order.get('customer_username', 'Unknown')}")
                                    st.markdown(f"**Date:** {format_datetime(order.get('order_date', ''))}")
                                    
                                    # Display meals
                                    if 'meals_for_chef' in order:
                                        st.markdown("**Ordered Items:**")
                                        for meal in order['meals_for_chef']:
                                            meal_name = meal.get('meal_name', 'unknown')
                                            quantity = int(meal.get('quantity', 1))
                                            price = float(meal.get('price', 0))
                                            st.markdown(f"- {meal_name} (x{quantity}) @ {format_currency(price)} each")
                                
                                with col2:
                                    st.markdown(f"**Total Value:** {format_currency(float(order.get('total_value_for_chef', 0)))}")
                                    st.markdown(f"**Payment:** {'Paid' if order.get('is_paid', False) else 'Pending'}")
                                    st.markdown(f"**Last Updated:** {format_datetime(order.get('updated_at', ''))}")
                                    
                                    # Order actions based on status
                                    status = order.get('status', '').lower()
                                    if status == 'placed':
                                        if st.button("Confirm Order", key=f"dash_confirm_{order.get('id')}"):
                                            st.success(f"Order #{order.get('id')} confirmed!")
                                            # Here you would add the API call to update status
                                    elif status == 'confirmed':
                                        if st.button("Mark Completed", key=f"dash_complete_{order.get('id')}"):
                                            st.success(f"Order #{order.get('id')} marked as completed!")
                                            # Here you would add the API call to update status
                                
                                if order.get('special_requests'):
                                    st.markdown(f"**Special Requests:** {order.get('special_requests')}")
                                
                                st.markdown("---")
                else:
                    st.info("You have no active orders at this time.")
            except Exception as e:
                logging.error(f"Error displaying active orders: {str(e)}")
                st.error("Error displaying active orders. Please try refreshing the page.")
            
            if orders:
                # Add debug logging to understand orders format
                logging.info(f"Orders type for analytics: {type(orders)}")
                if isinstance(orders, dict) and 'details' in orders:
                    logging.info(f"Orders has details key with type: {type(orders['details'])}")
                
                order_data = []
                
                # Handle both list format and dict with details.results format
                orders_list = orders
                if isinstance(orders, dict):
                    if 'details' in orders and isinstance(orders['details'], dict) and 'results' in orders['details']:
                        orders_list = orders['details']['results']
                    elif 'details' in orders and isinstance(orders['details'], list):
                        orders_list = orders['details']
                    elif 'results' in orders:
                        orders_list = orders['results']
                
                logging.info(f"Processing {len(orders_list) if isinstance(orders_list, list) else 'unknown'} orders for analytics")
                
                # Check if we need to extract orders from meal events
                if not isinstance(orders_list, list) or len(orders_list) == 0:
                    # Try to get orders from events
                    st.info("No order details found. Attempting to use meal events data instead.")
                    events = fetch_chef_meal_events(my_events=True)
                    if events and isinstance(events, list):
                        # Extract basic order data from events
                        for event in events:
                            if event.get('orders_count', 0) > 0:
                                event_date = event.get('event_date')
                                created_at = event.get('created_at')
                                price = float(event.get('current_price', 0))
                                quantity = int(event.get('orders_count', 0))
                                revenue = price * quantity
                                
                                # Use event created_at or event_date if available
                                date_to_use = created_at if created_at else f"{event_date}T00:00:00Z" if event_date else None
                                
                                if date_to_use:
                                    order_data.append({
                                        'created_at': date_to_use,
                                        'revenue': revenue
                                    })
                
                for order in (orders_list if isinstance(orders_list, list) else []):
                    try:
                        created_at = order.get('created_at')
                        price_paid = float(order.get('price_paid', 0))
                        quantity = int(order.get('quantity', 0))
                        revenue = price_paid * quantity
                        # Append the raw created_at value for conversion later
                        order_data.append({'created_at': created_at, 'revenue': revenue})
                        logging.info(f"Added order data: {created_at}, revenue: {revenue}")
                    except Exception as e:
                        logging.error(f"Error processing order for analytics: {str(e)}")
                        logging.error(f"Problematic order data: {order}")
                        continue
                if order_data:
                    df_orders = pd.DataFrame(order_data)
                    # Convert 'created_at' to datetime, coercing errors to NaT
                    df_orders['created_at'] = pd.to_datetime(df_orders['created_at'], errors='coerce')
                    # Drop rows with invalid or missing dates
                    df_orders = df_orders.dropna(subset=['created_at'])
                    # ---- Revenue & Earnings / Orders Overview ----
                    if not df_orders.empty:
                        # Identify the money column once
                        possible_price_cols = ['revenue', 'price_paid', 'total_price', 'unit_price', 'price']
                        price_col = next((col for col in possible_price_cols if col in df_orders.columns), None)

                        # Ensure we have something usable
                        if price_col:
                            # Guarantee a status column for downstream filters
                            if 'status' not in df_orders.columns:
                                df_orders['status'] = 'placed'

                            df_orders[price_col] = pd.to_numeric(df_orders[price_col], errors='coerce').fillna(0)

                            # ---- Revenue Summary ----
                            gross_sales = df_orders[price_col].sum()
                            refunded = df_orders.loc[df_orders['status'] == 'refunded', price_col].sum()
                            cancelled = df_orders.loc[df_orders['status'] == 'cancelled', price_col].sum()
                            net_sales = gross_sales - refunded - cancelled

                            st.markdown("### Revenue Summary")
                            col_gross, col_lost, col_net = st.columns(3)
                            col_gross.metric("Gross", format_currency(gross_sales))
                            col_lost.metric("Refunded / Cancelled", format_currency(refunded + cancelled))
                            col_net.metric("Net Earned", format_currency(net_sales))

                            # ---- Orders Overview ----
                            total_items = df_orders.shape[0]
                            total_quantity = (
                                pd.to_numeric(df_orders['quantity'], errors='coerce').fillna(1).sum()
                                if 'quantity' in df_orders.columns else total_items
                            )
                            total_value = gross_sales  # same as gross_sales already computed

                            st.markdown("### Orders Overview")
                            c_items, c_qty, c_val = st.columns(3)
                            c_items.metric("Items", int(total_items))
                            c_qty.metric("Total Quantity", int(total_quantity))
                            c_val.metric("Total Value", format_currency(total_value))

                            # Raw data for quick inspection
                            with st.expander("Order Data"):
                                st.dataframe(df_orders)
                        else:
                            st.warning("Couldn’t locate a price column in orders data.")
                    else:
                        st.info("No orders to display.")
                    # -----------------------------------------------------
                else:
                    st.info("No order data available for analytics.")
            else:
                st.info("No orders found for analytics.")
    
    # Tab 2: My Meal Events
    with tab2:
        st.header("My Meal Events")
        
        # Add refresh button that will trigger a rerun when clicked
        refresh_clicked = st.button("Refresh Events", key="refresh_events")
        if refresh_clicked:
            st.rerun()  # This will rerun the app and fetch fresh data
            
        # Fetch chef's meal events
        events = fetch_chef_meal_events(my_events=True)
        
        
        if events:
            try:
                # Split into upcoming and past events
                now = datetime.now().date()
                upcoming_events = []
                past_events = []
                
                for event in events:
                    if not isinstance(event, dict):
                        logging.error(f"Event is not a dictionary: {event}")
                        continue
                        
                    if 'event_date' not in event:
                        logging.error(f"Event missing event_date: {event}")
                        continue
                        
                    try:
                        event_date = datetime.strptime(event['event_date'], '%Y-%m-%d').date()
                        if event_date >= now:
                            upcoming_events.append(event)
                        else:
                            past_events.append(event)
                    except (ValueError, TypeError) as e:
                        logging.error(f"Invalid date format: {event['event_date']} - {str(e)}")
                        continue
                
                # Display upcoming events
                if upcoming_events:
                    st.subheader("Upcoming Events")
                    for event in upcoming_events:
                        with st.expander(f"{event['meal']['name']} - {format_date(event['event_date'])}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown(f"**Event Date:** {format_date(event['event_date'])}")
                                st.markdown(f"**Event Time:** {event['event_time']}")
                                st.markdown(f"**Order Cutoff:** {format_datetime(event['order_cutoff_time'])}")
                                st.markdown(f"**Status:** {event['status'].capitalize()}")
                            
                            with col2:
                                st.markdown(f"**Base Price:** {format_currency(event['base_price'])}")
                                st.markdown(f"**Current Price:** {format_currency(event['current_price'])}")
                                st.markdown(f"**Orders:** {event['orders_count']}/{event['max_orders']}")
                                
                                # Create unique keys for each event's state
                                cancel_state_key = f"cancel_state_{event['id']}"
                                edit_state_key = f"edit_state_{event['id']}"
                                
                                # Initialize the state keys if they don't exist
                                if cancel_state_key not in st.session_state:
                                    st.session_state[cancel_state_key] = "initial"
                                if edit_state_key not in st.session_state:
                                    st.session_state[edit_state_key] = "initial"
                                
                                # Only show action buttons if the event is not cancelled or completed
                                if event['status'] not in ['cancelled', 'completed']:
                                    # Create a row of buttons for actions
                                    action_col1, action_col2 = st.columns(2)
                                    
                                    with action_col1:
                                        # Edit button
                                        if st.session_state[edit_state_key] == "initial" and st.session_state[cancel_state_key] == "initial":
                                            if st.button("Edit Event", key=f"edit_{event['id']}"):
                                                st.session_state[edit_state_key] = "editing"
                                                st.rerun()
                                    
                                    with action_col2:
                                        # Cancel button - only show if not in edit mode
                                        if st.session_state[edit_state_key] == "initial":
                                            if st.session_state[cancel_state_key] == "initial":
                                                if st.button("Cancel Event", key=f"cancel_{event['id']}"):
                                                    st.session_state[cancel_state_key] = "reason_requested"
                                                    st.rerun()
                            
                            # Show edit form if in editing mode
                            if st.session_state.get(edit_state_key) == "editing":
                                st.markdown("---")
                                st.subheader("Edit Event")
                                
                                with st.form(key=f"edit_event_form_{event['id']}"):
                                    # Get all available meals for this chef
                                    meals = fetch_chef_meals()
                                    meal_options = {m['id']: m['name'] for m in meals}
                                    
                                    # Default values from current event
                                    current_meal_id = event['meal']['id']
                                    
                                    # Create meal selection dropdown
                                    meal_id = st.selectbox(
                                        "Select Meal", 
                                        options=list(meal_options.keys()),
                                        index=list(meal_options.keys()).index(current_meal_id) if current_meal_id in meal_options.keys() else 0,
                                        format_func=lambda x: meal_options[x]
                                    )
                                    
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        # Parse event date string to date object
                                        # Parse event date string to date object
                                        try:
                                            current_date = datetime.strptime(event['event_date'], '%Y-%m-%d').date()
                                        except (ValueError, TypeError):
                                            current_date = datetime.now().date() + timedelta(days=1)
                                        
                                        min_date = datetime.now().date() + timedelta(days=1)
                                        # Ensure the default date is not before the minimum allowed date
                                        default_date = current_date if current_date >= min_date else min_date
                                        
                                        event_date = st.date_input(
                                            "Event Date", 
                                            value=default_date,
                                            min_value=min_date
                                        )
                                        
                                        # Parse event time string to time object
                                        try:
                                            current_time = datetime.strptime(event['event_time'], '%H:%M').time()
                                        except (ValueError, TypeError):
                                            current_time = datetime.now().time().replace(hour=18, minute=0)
                                            
                                        event_time = st.time_input(
                                            "Event Time", 
                                            value=current_time
                                        )
                                        
                                        # Parse cutoff time string to datetime object
                                        try:
                                            cutoff_datetime = parse(event['order_cutoff_time'])
                                            cutoff_date = cutoff_datetime.date()
                                            cutoff_time = cutoff_datetime.time()
                                        except (ValueError, TypeError):
                                            cutoff_date = datetime.now().date()
                                            cutoff_time = datetime.now().time().replace(hour=12, minute=0)
                                        
                                        # Ensure cutoff date isn't before the minimum allowed date (today)
                                        min_cutoff_date = datetime.now().date()
                                        # Use the greater of the current cutoff date and min allowed date
                                        default_cutoff_date = max(cutoff_date, min_cutoff_date)
                                        
                                        cutoff_date = st.date_input(
                                            "Order Cutoff Date", 
                                            value=default_cutoff_date,
                                            min_value=min_cutoff_date
                                        )
                                        
                                        order_cutoff_time = st.time_input(
                                            "Order Cutoff Time", 
                                            value=cutoff_time
                                        )
                                    
                                    with col2:
                                        base_price = st.number_input(
                                            "Base Price ($)", 
                                            min_value=5.0, 
                                            step=1.0, 
                                            value=float(event['base_price'])
                                        )
                                        
                                        min_price = st.number_input(
                                            "Minimum Price ($)", 
                                            min_value=1.0, 
                                            step=1.0, 
                                            value=float(event['min_price']) if 'min_price' in event else max(5.0, float(event['base_price']) * 0.7),
                                            help="The lowest price you'll accept per meal as more people order. Cannot go below $1."
                                        )
                                        
                                        orders_count = int(event['orders_count'])
                                        max_orders = st.number_input(
                                            "Maximum Orders", 
                                            min_value=orders_count, 
                                            step=1, 
                                            value=int(event['max_orders'])
                                        )
                                        
                                        min_orders = st.number_input(
                                            "Minimum Orders", 
                                            min_value=1, 
                                            max_value=max_orders, 
                                            step=1, 
                                            value=int(event['min_orders']) if 'min_orders' in event else 3
                                        )
                                    
                                    description = st.text_area(
                                        "Event Description", 
                                        value=event['description']
                                    )
                                    
                                    special_instructions = st.text_area(
                                        "Special Instructions (Optional)", 
                                        value=event['special_instructions'] if 'special_instructions' in event else ""
                                    )
                                    
                                    # Validate cutoff time is before event time
                                    cutoff_datetime = datetime.combine(cutoff_date, order_cutoff_time)
                                    event_datetime = datetime.combine(event_date, event_time)
                                    if cutoff_datetime >= event_datetime:
                                        st.warning("Order cutoff time must be before event time.")
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        submit_button = st.form_submit_button("Update Event")
                                    with col2:
                                        cancel_button = st.form_submit_button("Cancel")
                                
                                if submit_button:
                                    # Format the cutoff time
                                    cutoff_datetime = datetime.combine(cutoff_date, order_cutoff_time)
                                    
                                    # Validate cutoff time is before event time
                                    event_datetime = datetime.combine(event_date, event_time)
                                    if cutoff_datetime >= event_datetime:
                                        st.error("Order cutoff time must be before event time. Please adjust and try again.")
                                    else:
                                        # Prepare the data
                                        data = {
                                            'meal': meal_id,
                                            'event_date': event_date.strftime('%Y-%m-%d'),
                                            'event_time': event_time.strftime('%H:%M'),
                                            'order_cutoff_time': cutoff_datetime.strftime('%Y-%m-%d %H:%M'),
                                            'base_price': base_price,
                                            'min_price': min_price,
                                            'max_orders': max_orders,
                                            'min_orders': min_orders,
                                            'description': description,
                                            'special_instructions': special_instructions
                                        }
                                        
                                        # Update the event
                                        result = update_chef_meal_event(event['id'], data)
                                        
                                        if result:
                                            if 'error' in result:
                                                st.error(result['error'])
                                            else:
                                                st.success("Event updated successfully!")
                                                # Reset the edit state
                                                st.session_state[edit_state_key] = "initial"
                                                time.sleep(1)  # Give user time to see the success message
                                                st.rerun()
                                
                                elif cancel_button:
                                    # Reset edit state
                                    st.session_state[edit_state_key] = "initial"
                                    st.rerun()
                                    
                            # Show cancellation UI if in cancel mode
                            elif st.session_state.get(cancel_state_key) == "reason_requested":
                                st.markdown("---")
                                st.subheader("Cancel Event")
                                reason = st.text_area("Reason for cancellation", key=f"reason_{event['id']}")
                                col1, col2 = st.columns([1, 1])
                                with col1:
                                    if st.button(f"Confirm Cancellation", key=f"confirm_{event['id']}"):
                                        if cancel_chef_meal_event(event['id'], reason):
                                            st.session_state[cancel_state_key] = "initial"
                                            st.success("Event cancelled successfully!")
                                            time.sleep(1)  # Give user time to see the success message
                                            st.rerun()
                                with col2:
                                    if st.button("Cancel", key=f"back_{event['id']}"):
                                        st.session_state[cancel_state_key] = "initial"
                                        st.rerun()
                            
                            # Only show description if not in edit or cancel mode
                            elif st.session_state.get(edit_state_key) == "initial" and st.session_state.get(cancel_state_key) == "initial":
                                st.markdown(f"**Description:** {event['description']}")
                                if event['special_instructions']:
                                    st.markdown(f"**Special Instructions:** {event['special_instructions']}")
                else:
                    st.info("You don't have any upcoming meal events.")
                
                # Display past events
                if past_events:
                    st.subheader("Past Events")
                    past_df = pd.DataFrame([
                        {
                            'Event Date': format_date(e['event_date']),
                            'Meal': e['meal']['name'],
                            'Orders': e['orders_count'],
                            'Revenue': format_currency(float(e['current_price']) * e['orders_count']),
                            'Status': e['status'].capitalize()
                        } for e in past_events
                    ])
                    
                    st.dataframe(past_df)
            except Exception as e:
                st.error(f"Error processing meal events: {str(e)}")
                logging.error(f"Error processing meal events: {str(e)}")
                logging.error(traceback.format_exc())
        else:
            st.info("You haven't created any meal events yet.")
            st.button("Create your first meal event", on_click=lambda: st.session_state.update({'active_tab': 'Create Event'}))
    
    # Tab 3: Received Orders
    with tab3:
        st.header("Received Orders")
        
        # Fetch orders as chef
        orders = fetch_chef_meal_orders(as_chef=True)
        logging.info(f"Orders received in tab3: Type={type(orders)}, Content={orders}")

        # Add refresh button
        if st.button("Refresh Orders", key="refresh_orders_tab3"):
            st.rerun()

        # Add fulfillment management section
        st.subheader("Order Fulfillment Management")
        
        # Initialize session state for fulfillment management if needed
        if 'fulfillment_events' not in st.session_state:
            st.session_state['fulfillment_events'] = {}
        
        # Initialize lists for processing
        events_with_orders = []
        all_orders = []
        
        try:
            # Handle the case where orders is a list (direct orders)
            if isinstance(orders, list):
                # Group orders by meal if possible
                orders_by_meal = {}
                for order in orders:
                    # This is simpler than our previous implementation since we don't have events
                    # We'll create synthetic event groupings based on meals
                    # Look for meal information in the order
                    primary_meal = None
                    if 'meals_for_chef' in order and order['meals_for_chef']:
                        primary_meal = order['meals_for_chef'][0].get('meal_name', 'Unnamed Meal')
                    else:
                        primary_meal = "Ungrouped Orders"
                    
                    # Add to the appropriate group
                    if primary_meal not in orders_by_meal:
                        orders_by_meal[primary_meal] = {
                            'id': f"synthetic_{primary_meal.replace(' ', '_')}",
                            'meal': {'name': primary_meal},
                            'event_date': order.get('order_date', '').split('T')[0] if order.get('order_date') else 'Unknown Date',
                            'event_time': 'Varies',
                            'current_price': order.get('total_value_for_chef', 0),
                            'orders_count': 0,
                            'max_orders': 999,
                            'active_orders': []
                        }
                    
                    # Add this order to the appropriate group
                    orders_by_meal[primary_meal]['active_orders'].append(order)
                    orders_by_meal[primary_meal]['orders_count'] += 1
                    all_orders.append(order)
                
                # Convert our groups to a list
                for meal_name, event_data in orders_by_meal.items():
                    events_with_orders.append(event_data)
            
            # Also handle the original dictionary format for backward compatibility
            elif isinstance(orders, dict) and 'details' in orders and 'results' in orders['details']:
                events = orders['details']['results']
                now = datetime.now().date()
                logging.info(f"Current date: {now}")
                
                for event in events:
                    event_id = event.get('id')
                    
                    # Check if event has active orders - add ALL events with active orders
                    if 'active_orders' in event and event['active_orders']:
                        logging.info(f"Event {event_id} has active orders. Adding to display list.")
                        events_with_orders.append(event)
                        all_orders.extend(event['active_orders'])
                
                # Log the events we found
                logging.info(f"Found {len(events_with_orders)} events with active orders: {[e.get('id') for e in events_with_orders]}")
            
            # Sort events by date (most recent first)
            events_with_orders.sort(key=lambda x: x.get('event_date', '9999-12-31'), reverse=True)
            
            # Create summary metrics for all orders
            status_counts = {}
            for order in all_orders:
                status = order.get('status', 'unknown').lower()
                status_counts[status] = status_counts.get(status, 0) + 1
                
            # Display order status metrics
            st.subheader("Order Status Summary")
            cols = st.columns(5)
            with cols[0]:
                st.metric("Total Orders", len(all_orders))
            with cols[1]:
                st.metric("Placed", status_counts.get('placed', 0))
            with cols[2]:
                st.metric("Confirmed", status_counts.get('confirmed', 0))
            with cols[3]:
                st.metric("Completed", status_counts.get('completed', 0))
            with cols[4]:
                st.metric("Cancelled", status_counts.get('cancelled', 0) + status_counts.get('refunded', 0))
        
        except Exception as e:
            logging.error(f"Error processing events for fulfillment: {str(e)}")
            logging.error(traceback.format_exc())
        
        if events_with_orders:
            # Display fulfillment summary
            with st.container():
                st.markdown("### Orders by Meal/Event")
                st.info("Showing all meals/events with active orders")
                
                for event in events_with_orders:
                    # Create a unique key for this event in session state
                    event_key = f"event_{event['id']}"
                    if event_key not in st.session_state['fulfillment_events']:
                        st.session_state['fulfillment_events'][event_key] = {
                            'expanded': False,
                            'selected_orders': []
                        }
                    
                    # Format event date and time information
                    try:
                        event_date = datetime.strptime(event['event_date'], '%Y-%m-%d').date()
                        days_until = (event_date - datetime.now().date()).days
                        if days_until > 0:
                            time_status = f"📅 {days_until} days away"
                        elif days_until == 0:
                            time_status = "📅 Today"
                        else:
                            time_status = f"🕒 {abs(days_until)} days ago"
                    except (ValueError, TypeError):
                        time_status = "📋 Unknown date"
                    
                    # Create expander label with order count
                    order_count = len(event['active_orders'])
                    meal_name = event['meal']['name'] if isinstance(event['meal'], dict) else event.get('meal', 'Unnamed Meal')
                    expander_label = f"{meal_name} - {format_date(event['event_date'])} ({time_status}) - {order_count} order(s)"
                    
                    # Event card with order summary
                    with st.expander(expander_label, expanded=st.session_state['fulfillment_events'][event_key]['expanded']):
                        # Toggle expanded state when clicked
                        st.session_state['fulfillment_events'][event_key]['expanded'] = True
                        
                        # Show a warning for past events
                        if 'days_until' in locals() and days_until < 0:
                            st.warning(f"⚠️ This event is in the past ({abs(days_until)} days ago)")
                        
                        # Show event details
                        col1, col2 = st.columns([3, 2])
                        with col1:
                            if 'event_time' in event:
                                st.markdown(f"**Event Time:** {event['event_time']}")
                            st.markdown(f"**Current Price:** {format_currency(float(event.get('current_price', 0)))}")
                            st.markdown(f"**Orders:** {event.get('orders_count', len(event['active_orders']))}/{event.get('max_orders', 'unlimited')}")
                        
                        with col2:
                            # Display order status breakdown for this event
                            status_counts = {'placed': 0, 'confirmed': 0, 'completed': 0, 'cancelled': 0}
                            total_revenue = 0
                            
                            for order in event['active_orders']:
                                status = order.get('status', 'unknown').lower()
                                status_counts[status] = status_counts.get(status, 0) + 1
                                total_revenue += float(order.get('total_value_for_chef', 0))
                            
                            st.markdown("**Order Status Counts:**")
                            st.markdown(f"- Placed: {status_counts.get('placed', 0)}")
                            st.markdown(f"- Confirmed: {status_counts.get('confirmed', 0)}")
                            st.markdown(f"- Completed: {status_counts.get('completed', 0)}")
                            st.markdown(f"- Cancelled: {status_counts.get('cancelled', 0)}")
                            st.markdown(f"**Total Revenue:** {format_currency(total_revenue)}")
                        
                        # Display active orders for this event with action buttons
                        # TODO: Verify whether the order date is based on when the plan was created or when the order was placed
                        if 'active_orders' in event and event['active_orders']:
                            st.markdown("### Orders")
                            # Create tabs for different status groups
                            order_tabs = st.tabs(["All Orders", "Placed", "Confirmed", "Completed", "Cancelled"])
                            
                            with order_tabs[0]:  # All Orders tab
                                orders_table_data = []
                                for order in event['active_orders']:
                                    # Get meal information
                                    meal_details = []
                                    if 'meals_for_chef' in order:
                                        for meal in order['meals_for_chef']:
                                            meal_name = meal.get('meal_name', 'unknown')
                                            quantity = meal.get('quantity', 1)
                                            meal_details.append(f"{meal_name} (x{quantity})")
                                    
                                    orders_table_data.append({
                                        'Order ID': order.get('id', 'N/A'),
                                        'Customer': order.get('customer_username', 'Unknown'),
                                        'Status': order.get('status', 'unknown').upper(),
                                        'Items': ", ".join(meal_details),
                                        'Total Quantity': order.get('quantity', 1),
                                        'Total Value': format_currency(float(order.get('total_value_for_chef', 0))),
                                        'Order Date': format_datetime(order.get('order_date', order.get('created_at', ''))),
                                        'Updated': format_datetime(order.get('updated_at', ''))
                                    })
                                
                                if orders_table_data:
                                    st.dataframe(orders_table_data, use_container_width=True)
                                else:
                                    st.info("No orders available")
                            
                            # Placed orders tab
                            with order_tabs[1]:
                                placed_orders = [o for o in event['active_orders'] if o.get('status', '').lower() == 'placed']
                                for order in placed_orders:
                                    with st.container():
                                        col1, col2, col3 = st.columns([4, 2, 2])
                                        with col1:
                                            st.markdown(f"**Order #{order.get('id', 'N/A')} - {order.get('customer_username', order.get('customer_name', 'Unknown'))}**")
                                            
                                            # Show meal items if available
                                            if 'meals_for_chef' in order:
                                                st.markdown("**Items:**")
                                                for meal in order['meals_for_chef']:
                                                    meal_name = meal.get('meal_name', 'Unknown')
                                                    quantity = meal.get('quantity', 1)
                                                    price = meal.get('price', 0)
                                                    st.markdown(f"- {meal_name} (x{quantity}) @ {format_currency(float(price))}")
                                            else:
                                                st.markdown(f"**Quantity:** {order.get('quantity', 1)}")
                                                
                                            if order.get('special_requests'):
                                                st.markdown(f"**Special Requests:** {order.get('special_requests')}")
                                        
                                        with col2:
                                            st.markdown(f"**Total Value:** {format_currency(float(order.get('total_value_for_chef', 0)))}")
                                            st.markdown(f"**Payment:** {'Paid' if order.get('is_paid', False) else 'Pending'}")
                                            st.markdown(f"**Order Date:** {format_datetime(order.get('order_date', order.get('created_at', '')))}")
                                        
                                        with col3:
                                            if st.button("Confirm Order", key=f"confirm_btn_{order.get('id', 'unknown')}"):
                                                # Call the confirm function
                                                if confirm_chef_meal_order(order.get('id', 'unknown')):
                                                    st.success(f"Order #{order.get('id', 'unknown')} confirmed!")
                                                    time.sleep(1)  # Give the user a moment to see the success message
                                                    st.rerun()  # Refresh the page to update the order status
                            
                                        st.markdown("---")
                                
                                if not placed_orders:
                                    st.info("No placed orders")
                            
                            # Confirmed orders tab
                            with order_tabs[2]:
                                confirmed_orders = [o for o in event['active_orders'] if o.get('status', '').lower() == 'confirmed']
                                for order in confirmed_orders:
                                    with st.container():
                                        col1, col2, col3 = st.columns([4, 2, 2])
                                        with col1:
                                            st.markdown(f"**Order #{order.get('id', 'N/A')} - {order.get('customer_username', order.get('customer_name', 'Unknown'))}**")
                                            
                                            # Show meal items if available
                                            if 'meals_for_chef' in order:
                                                st.markdown("**Items:**")
                                                for meal in order['meals_for_chef']:
                                                    meal_name = meal.get('meal_name', 'Unknown')
                                                    quantity = meal.get('quantity', 1)
                                                    price = meal.get('price', 0)
                                                    st.markdown(f"- {meal_name} (x{quantity}) @ {format_currency(float(price))}")
                                            else:
                                                st.markdown(f"**Quantity:** {order.get('quantity', 1)}")
                                                
                                            if order.get('special_requests'):
                                                st.markdown(f"**Special Requests:** {order.get('special_requests')}")
                                        
                                        with col2:
                                            st.markdown(f"**Total Value:** {format_currency(float(order.get('total_value_for_chef', 0)))}")
                                            st.markdown(f"**Payment:** {'Paid' if order.get('is_paid', False) else 'Pending'}")
                                            st.markdown(f"**Order Date:** {format_datetime(order.get('order_date', order.get('created_at', '')))}")
                                        
                                        with col3:
                                            if st.button("Mark Completed", key=f"complete_btn_{order.get('id', 'unknown')}"):
                                                # Here would be API call to update order status
                                                st.success(f"Order #{order.get('id', 'unknown')} marked as completed!")
                                                # In a real implementation, you would update the order status
                            
                                        st.markdown("---")
                                
                                if not confirmed_orders:
                                    st.info("No confirmed orders")
                                
                            # Completed orders tab
                            with order_tabs[3]:
                                completed_orders = [o for o in event['active_orders'] if o.get('status', '').lower() == 'completed']
                                if completed_orders:
                                    completed_df = pd.DataFrame([
                                        {
                                            'Order ID': o.get('id', 'N/A'),
                                            'Customer': o.get('customer_username', o.get('customer_name', 'Unknown')),
                                            'Items': ', '.join([f"{m.get('meal_name', 'Unknown')} (x{m.get('quantity', 1)})" 
                                                              for m in o.get('meals_for_chef', [])]) if 'meals_for_chef' in o else 'Unknown',
                                            'Quantity': sum([m.get('quantity', 1) for m in o.get('meals_for_chef', [])]) if 'meals_for_chef' in o else o.get('quantity', 1),
                                            'Total': format_currency(float(o.get('total_value_for_chef', 0))),
                                            'Completed At': format_datetime(o.get('updated_at', o.get('order_date', o.get('created_at', ''))))
                                        } for o in completed_orders
                                    ])
                                    st.dataframe(completed_df)
                                else:
                                    st.info("No completed orders")
                            
                            # Cancelled orders tab
                            with order_tabs[4]:
                                cancelled_orders = [o for o in event['active_orders'] if o.get('status', '').lower() in ['cancelled', 'refunded']]
                                if cancelled_orders:
                                    cancelled_df = pd.DataFrame([
                                        {
                                            'Order ID': o.get('id', 'N/A'),
                                            'Customer': o.get('customer_username', o.get('customer_name', 'Unknown')),
                                            'Status': o.get('status', 'Unknown').capitalize(),
                                            'Items': ', '.join([f"{m.get('meal_name', 'Unknown')} (x{m.get('quantity', 1)})"
                                                              for m in o.get('meals_for_chef', [])]) if 'meals_for_chef' in o else 'Unknown',
                                            'Total': format_currency(float(o.get('total_value_for_chef', 0))),
                                            'Cancelled At': format_datetime(o.get('updated_at', o.get('order_date', o.get('created_at', ''))))
                                        } for o in cancelled_orders
                                    ])
                                    st.dataframe(cancelled_df)
                                else:
                                    st.info("No cancelled orders")
                        
                        # No active orders message
                        if not event['active_orders']:
                            st.info("No active orders for this event.")
                
                # Clear expanded state for other events when navigating away
                for key in st.session_state['fulfillment_events']:
                    if key != event_key:
                        st.session_state['fulfillment_events'][key]['expanded'] = False
        else:
            st.info("You have no upcoming events with orders.")
            
            # Show a call to action to create an event
            if st.button("Create a New Event"):
                # Navigate to create event tab in a real implementation
                pass

        # # Status filter for orders
        # st.subheader("All Orders")
        # status_filter = st.multiselect(
        #     "Filter by Status",
        #     options=["placed", "confirmed", "completed", "cancelled", "refunded"],
        #     default=["placed", "confirmed"],
        #     format_func=lambda x: x.capitalize()
        # )
        
        # try:
        #     # Initialize containers for different order types
        #     active_orders = []
        #     completed_orders = []
        #     cancelled_orders = []
            
        #     # Process orders data structure
        #     if isinstance(orders, dict) and 'details' in orders and 'results' in orders['details']:
        #         events = orders['details']['results']
        #         logging.info(f"Processing {len(events)} events for the 'All Orders' section.")
                
        #         # Extract orders from all events
        #         for i, event in enumerate(events):
        #             event_id = event.get('id')
        #             logging.debug(f"Processing event {i+1}/{len(events)}, ID: {event_id}")
                    
        #             # Check if 'active_orders' key exists and is a non-empty list
        #             if 'active_orders' in event and isinstance(event['active_orders'], list) and event['active_orders']:
        #                 logging.debug(f"Event {event_id} has {len(event['active_orders'])} active orders. Extracting...")
                        
        #                 event_date = event.get('event_date', '')
        #                 event_time = event.get('event_time', '')
        #                 meal_name = event['meal']['name'] if 'meal' in event and 'name' in event['meal'] else 'Unknown Meal'
        #                 meal_image = event['meal'].get('image', None)
                    
        #                 # Process active orders for this event
        #                 for order in event['active_orders']:
        #                     # Add event context to the order
        #                     try:
        #                         order['event_id'] = event_id
        #                         order['event_date'] = event_date
        #                         order['event_time'] = event_time
        #                         order['meal_name'] = meal_name
        #                         order['meal_image'] = meal_image
                                
        #                         # Sort into appropriate lists
        #                         order_status = order.get('status')
        #                         order_id = order.get('id', 'Unknown ID') # Get order ID for logging
                                
        #                         if order_status in ['placed', 'confirmed']:
        #                             active_orders.append(order)
        #                             logging.debug(f"Successfully processed and added active order {order_id} with status '{order_status}'.")
        #                         elif order_status == 'completed':
        #                             completed_orders.append(order)
        #                             logging.debug(f"Processed completed order {order_id}.")
        #                         elif order_status in ['cancelled', 'refunded']:
        #                             cancelled_orders.append(order)
        #                             logging.debug(f"Processed cancelled/refunded order {order_id}.")
        #                         else:
        #                             logging.warning(f"Order {order_id} has unknown status: '{order_status}'")
                                    
        #                     except Exception as order_error:
        #                         order_id_for_error = order.get('id', 'Unknown ID')
        #                         logging.error(f"Error processing order {order_id_for_error} within event {event_id}: {str(order_error)}")
        #                         logging.error(f"Problematic order data: {order}")
        #                         # Continue to next order instead of stopping
        #                         continue 
        #             else:
        #                 # Log if active_orders is missing, not a list, or empty
        #                 if 'active_orders' not in event:
        #                     logging.warning(f"Event {event_id} is missing 'active_orders' key.")
        #                 elif not isinstance(event.get('active_orders'), list):
        #                     logging.warning(f"Event {event_id} 'active_orders' is not a list (type: {type(event.get('active_orders'))}).")
        #                 elif not event.get('active_orders'):
        #                     logging.debug(f"Event {event_id} has an empty 'active_orders' list.")
            
        #     logging.info(f"Finished processing events. Found {len(active_orders)} active, {len(completed_orders)} completed, {len(cancelled_orders)} cancelled orders.")
        #     # Log the content of active_orders before filtering for debugging
        #     logging.debug(f"Active orders before filtering: {active_orders}")
        #     logging.debug(f"Current status filter: {status_filter}")
            
        #     # Display counts at the top
        #     col1, col2, col3 = st.columns(3)
        #     with col1:
        #         st.metric("Active Orders", len(active_orders))
        #     with col2:
        #         st.metric("Completed Orders", len(completed_orders))
        #     with col3:
        #         st.metric("Cancelled Orders", len(cancelled_orders))
            
        #     # Display active orders
        #     filtered_active = [o for o in active_orders if o['status'] in status_filter]
        #     if filtered_active:
        #         st.subheader("Active Orders")
        #         for order in filtered_active:
        #             with st.expander(f"Order #{order['id']} - {order['customer_name']} - {order['status'].upper()}"):
        #                 col1, col2 = st.columns([3, 2])
                        
        #                 with col1:
        #                     st.markdown(f"**Meal:** {order['meal_name']}")
        #                     st.markdown(f"**Event Date:** {format_date(order['event_date'])} at {order['event_time']}")
        #                     st.markdown(f"**Quantity:** {order.get('quantity', 1)}")
        #                     price = float(order.get('price_paid', 0))
        #                     quantity = int(order.get('quantity', 1))
        #                     st.markdown(f"**Price Paid:** {format_currency(price * quantity)}")
                        
        #                 with col2:
        #                     st.markdown(f"**Status:** {order['status'].capitalize()}")
        #                     st.markdown(f"**Order Date:** {format_datetime(order['created_at'])}")
        #                     st.markdown(f"**Delivery Method:** {order.get('delivery_method', 'Not specified')}")
                            
        #                     # Show address if available and not empty
        #                     address = order.get('address', {})
        #                     if address and any(address.values()):
        #                         address_parts = []
        #                         for key in ['street', 'city', 'state', 'postal_code', 'country']:
        #                             if address.get(key):
        #                                 address_parts.append(address[key])
        #                         if address_parts:
        #                             st.markdown(f"**Address:** {', '.join(address_parts)}")
                            
        #                     # Button to mark as completed if event date has passed
        #                     event_date = datetime.strptime(order['event_date'], '%Y-%m-%d').date()
        #                     if order['status'] == 'confirmed' and event_date <= datetime.now().date():
        #                         if st.button(f"Mark as Completed", key=f"complete_{order['id']}"):
        #                             # Implement the completion logic here
        #                             st.success("Order marked as completed!")
        #                             st.rerun()
                    
        #                 if order.get('special_requests'):
        #                     st.markdown(f"**Special Requests:** {order['special_requests']}")
        #     else:
        #         if "placed" in status_filter or "confirmed" in status_filter:
        #             st.info("You don't have any active orders matching the selected filters.")
            
        #     # Display completed orders in a table
        #     filtered_completed = [o for o in completed_orders if o['status'] in status_filter]
        #     if filtered_completed and "completed" in status_filter:
        #         st.subheader("Completed Orders")
        #         completed_df = pd.DataFrame([
        #             {
        #                 'Order Date': format_datetime(o['created_at']),
        #                 'Customer': o['customer_name'],
        #                 'Meal': o['meal_name'],
        #                 'Event Date': format_date(o['event_date']),
        #                 'Quantity': o.get('quantity', 1),
        #                 'Total': format_currency(float(o.get('price_paid', 0)) * int(o.get('quantity', 1)))
        #             } for o in filtered_completed
        #         ])
                
        #         st.dataframe(completed_df)
            
        #     # Display cancelled orders in a table
        #     filtered_cancelled = [o for o in cancelled_orders if o['status'] in status_filter]
        #     if filtered_cancelled and any(s in status_filter for s in ["cancelled", "refunded"]):
        #         st.subheader("Cancelled Orders")
        #         cancelled_df = pd.DataFrame([
        #             {
        #                 'Order Date': format_datetime(o['created_at']),
        #                 'Customer': o['customer_name'],
        #                 'Meal': o['meal_name'],
        #                 'Event Date': format_date(o['event_date']),
        #                 'Status': o['status'].capitalize(),
        #                 'Refunded': 'Yes' if o['status'] == 'refunded' else 'No'
        #             } for o in filtered_cancelled
        #         ])
                
        #         st.dataframe(cancelled_df)
                
        #     if not filtered_active and not filtered_completed and not filtered_cancelled:
        #         st.warning("No orders match your selected filters. Try changing the status filter.")
        # except Exception as e:
        #     st.error(f"Error processing orders: {str(e)}")
        #     logging.error(f"Error processing orders: {str(e)}")
        #     logging.error(traceback.format_exc())

        # if not orders or (isinstance(orders, dict) and not orders.get('details', {}).get('results', [])):
        #     st.info("You haven't received any orders yet.")
    
    # Tab 4: Manage Meals
    with tab4:
        st.header("Manage Meals")
        
        # Add helpful info about meal creation
        st.info("Create meals that can be used in your chef events. Once created, meals can be selected when creating a new event.")
        
        # Check if Stripe account is active
        stripe_status = check_stripe_account_status()
        if not stripe_status.get('is_active', False):
            st.warning("You need to set up your Stripe account before creating meals.")
            if st.button("Set Up Stripe Account", key="setup_stripe_create_meal"):
                stripe_url = create_stripe_account()
                if stripe_url:
                    st.success("Stripe account creation initiated. Click the link below to continue:")
                    st.markdown(f"[Complete Stripe Onboarding]({stripe_url})")
            return
        
        # Create tabs for ingredients, dishes, and meals
        ingr_tab, dish_tab, meal_tab, meal_manage_tab = st.tabs(["Manage Ingredients", "Manage Dishes", "Create Meal", "Manage Meals"])
        
        # Tab for managing ingredients
        with ingr_tab:
            st.subheader("Manage Ingredients")
            st.info("Create and manage ingredients that will be used in your dishes.")
            
            # Create ingredient form
            with st.expander("Create New Ingredient", expanded=False):
                with st.form("create_ingredient_form"):
                    ingredient_name = st.text_input("Ingredient Name", placeholder="Enter a name for your ingredient")
                    
                    st.subheader("Nutritional Information (per serving)")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        calories = st.number_input("Calories", min_value=0.0, step=1.0, value=0.0)
                        fat = st.number_input("Fat (g)", min_value=0.0, step=0.1, value=0.0)
                    
                    with col2:
                        carbs = st.number_input("Carbohydrates (g)", min_value=0.0, step=0.1, value=0.0)
                        protein = st.number_input("Protein (g)", min_value=0.0, step=0.1, value=0.0)
                    
                    ingredient_submit = st.form_submit_button("Create Ingredient")
                
                if ingredient_submit:
                    if not ingredient_name:
                        st.error("Ingredient name is required")
                    else:
                        data = {
                            'name': ingredient_name,
                            'calories': calories,
                            'fat': fat,
                            'carbohydrates': carbs,
                            'protein': protein
                        }
                        
                        result = create_chef_ingredient(data)
                        
                        if result and result.get('status') == 'success':
                            st.success("Ingredient created successfully!")
                            if 'details' in result:
                                st.info(f"Created ingredient: {result['details'].get('name')}")
                            st.rerun()  # Refresh to show new ingredient
            
            # Fetch and display chef's ingredients
            chef_ingredients = fetch_chef_ingredients()
            
            if not chef_ingredients:
                st.warning("You don't have any ingredients yet. Use the 'Create New Ingredient' section above to create ingredients.")
            else:
                # Display ingredients with edit/delete options
                st.subheader("Your Ingredients")
                
                # Check if we're in edit mode for a specific ingredient
                edit_ingredient_id = st.session_state.get('edit_ingredient_id', None)
                
                # Display ingredients in a table format
                ingredient_table_data = []
                for ingredient in chef_ingredients:
                    ingredient_table_data.append({
                        'Name': ingredient['name'],
                        'Calories': f"{float(ingredient.get('calories', 0)):.0f}",
                        'Fat (g)': f"{float(ingredient.get('fat', 0)):.1f}",
                        'Carbs (g)': f"{float(ingredient.get('carbohydrates', 0)):.1f}",
                        'Protein (g)': f"{float(ingredient.get('protein', 0)):.1f}",
                        'id': ingredient['id']
                    })
                
                # Create a DataFrame for display
                if ingredient_table_data:
                    # Create a DataFrame from ingredient data
                    df = pd.DataFrame(ingredient_table_data)
                    
                    # Configure column display
                    column_config = {
                        "Name": st.column_config.TextColumn(
                            "Name",
                            help="Ingredient name",
                            width="medium"
                        ),
                        "Calories": st.column_config.NumberColumn(
                            "Calories",
                            help="Calories per serving",
                            format="%d",
                            width="small"
                        ),
                        "Fat (g)": st.column_config.NumberColumn(
                            "Fat (g)",
                            help="Fat content in grams",
                            format="%.1f g",
                            width="small"
                        ),
                        "Carbs (g)": st.column_config.NumberColumn(
                            "Carbs (g)",
                            help="Carbohydrate content in grams",
                            format="%.1f g",
                            width="small"
                        ),
                        "Protein (g)": st.column_config.NumberColumn(
                            "Protein (g)",
                            help="Protein content in grams",
                            format="%.1f g",
                            width="small"
                        ),
                        "id": st.column_config.Column(
                            "ID",
                            help="Internal ID",
                            width="small",
                            disabled=True
                        )
                    }
                    
                    # Center the table
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col2:
                        st.dataframe(
                            df,
                            column_config=column_config,
                            use_container_width=True,
                            hide_index=True
                        )
                    
                    # Rest of the management interface remains the same
                    st.subheader("Manage Ingredients")

                    # Display a cleaner interface for each ingredient
                    for i, ingredient in enumerate(ingredient_table_data):
                        # Use an expander for each ingredient to save space
                        with st.expander(f"**{ingredient['Name']}**"):
                            cols = st.columns([3, 1, 1])
                            
                            with cols[0]:
                                st.write(f"**Nutrition:** {ingredient['Calories']} cal | {ingredient['Fat (g)']}g fat | {ingredient['Carbs (g)']}g carbs | {ingredient['Protein (g)']}g protein")
                            
                            with cols[1]:
                                if st.button("✏️ Edit", key=f"edit_{ingredient['id']}"):
                                    st.session_state['edit_ingredient_id'] = ingredient['id']
                                    st.rerun()
                            
                            with cols[2]:
                                # Use session state to track deletion confirmation state
                                deletion_key = f"confirm_delete_{ingredient['id']}"
                                if deletion_key not in st.session_state:
                                    st.session_state[deletion_key] = False
                                
                                if not st.session_state[deletion_key]:
                                    if st.button("🗑️ Delete", key=f"delete_{ingredient['id']}"):
                                        st.session_state[deletion_key] = True
                                        st.rerun()
                                else:
                                    st.error("Confirm deletion?")
                                    c1, c2 = st.columns(2)
                                    with c1:
                                        if st.button("✓ Yes", key=f"confirm_{ingredient['id']}"):
                                            result = delete_chef_ingredient(ingredient['id'])
                                            if result and result.get('status') == 'success':
                                                st.success("Deleted!")
                                                st.session_state[deletion_key] = False
                                                st.rerun()
                                    with c2:
                                        if st.button("✗ No", key=f"cancel_{ingredient['id']}"):
                                            st.session_state[deletion_key] = False
                                            st.rerun()
                
                # Edit ingredient form if an ingredient is selected for editing
                if edit_ingredient_id:
                    # Get the ingredient details
                    edit_ingredient = next((i for i in chef_ingredients if i['id'] == edit_ingredient_id), None)
                    
                    if edit_ingredient:
                        st.subheader(f"Edit Ingredient: {edit_ingredient['name']}")
                        
                        with st.form(key=f"edit_ingredient_form_{edit_ingredient_id}"):
                            new_name = st.text_input("Ingredient Name", value=edit_ingredient['name'])
                            
                            st.subheader("Nutritional Information (per serving)")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                calories = st.number_input("Calories", 
                                                         min_value=0.0, 
                                                         step=1.0, 
                                                         value=float(edit_ingredient.get('calories', 0)))
                                fat = st.number_input("Fat (g)", 
                                                    min_value=0.0, 
                                                    step=0.1, 
                                                    value=float(edit_ingredient.get('fat', 0)))
                            
                            with col2:
                                carbs = st.number_input("Carbohydrates (g)", 
                                                      min_value=0.0, 
                                                      step=0.1, 
                                                      value=float(edit_ingredient.get('carbohydrates', 0)))
                                protein = st.number_input("Protein (g)", 
                                                        min_value=0.0, 
                                                        step=0.1, 
                                                        value=float(edit_ingredient.get('protein', 0)))
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                submit_edit = st.form_submit_button("Save Changes")
                            with col2:
                                cancel_edit = st.form_submit_button("Cancel")
                        
                        if submit_edit:
                            if not new_name:
                                st.error("Ingredient name is required")
                            else:
                                data = {
                                    'name': new_name,
                                    'calories': calories,
                                    'fat': fat,
                                    'carbohydrates': carbs,
                                    'protein': protein
                                }
                                
                                result = update_chef_ingredient(edit_ingredient_id, data)
                                
                                if result and result.get('status') == 'success':
                                    st.success("Ingredient updated successfully!")
                                    # Clear edit mode
                                    if 'edit_ingredient_id' in st.session_state:
                                        del st.session_state['edit_ingredient_id']
                                    st.rerun()
                        
                        if cancel_edit:
                            # Clear edit mode
                            if 'edit_ingredient_id' in st.session_state:
                                del st.session_state['edit_ingredient_id']
                            st.rerun()
        
        # Tab for managing dishes
        with dish_tab:
            st.subheader("Manage Dishes")
            st.info("Create dishes by combining ingredients. Dishes can be used in your meals.")
            
            # Create dish section
            with st.expander("Create New Dish", expanded=False):
                st.subheader("Create a New Dish")
                
                with st.form("create_dish_form"):
                    dish_name = st.text_input("Dish Name", placeholder="Enter a name for your dish")
                    featured = st.checkbox("Featured Dish", value=False, help="Mark this dish as featured")
                    
                    # Get ingredients for selection
                    available_ingredients = fetch_chef_ingredients()
                    if available_ingredients:
                        ingredient_options = {str(ing['id']): ing['name'] for ing in available_ingredients}
                        selected_ingredients = st.multiselect(
                            "Select Ingredients",
                            options=list(ingredient_options.keys()),
                            format_func=lambda x: ingredient_options.get(x, f"Ingredient {x}"),
                            help="Select ingredients that make up this dish"
                        )
                        
                        # Show nutritional information preview
                        if selected_ingredients:
                            st.markdown("### Nutritional Information Preview")
                            total_calories = 0
                            total_fat = 0
                            total_carbs = 0
                            total_protein = 0
                            
                            st.write("Selected Ingredients:")
                            for ing_id in selected_ingredients:
                                ingredient = next((i for i in available_ingredients if str(i['id']) == ing_id), None)
                                if ingredient:
                                    st.write(f"- {ingredient['name']}")
                                    total_calories += float(ingredient.get('calories', 0))
                                    total_fat += float(ingredient.get('fat', 0))
                                    total_carbs += float(ingredient.get('carbohydrates', 0))
                                    total_protein += float(ingredient.get('protein', 0))
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Calories", f"{total_calories:.0f}")
                                st.metric("Fat", f"{total_fat:.1f}g")
                            with col2:
                                st.metric("Carbohydrates", f"{total_carbs:.1f}g")
                                st.metric("Protein", f"{total_protein:.1f}g")
                    else:
                        st.warning("You need to create ingredients first.")
                        selected_ingredients = []
                    
                    dish_submit = st.form_submit_button("Create Dish")
                
                if dish_submit:
                    if not dish_name:
                        st.error("Dish name is required")
                    else:
                        data = {
                            'name': dish_name,
                            'featured': featured,
                            'ingredients': selected_ingredients
                        }
                        
                        result = create_chef_dish(data)
                        if result:
                            st.success("Dish created successfully!")
                            st.rerun()
        
        # Tab for creating meals
        with meal_tab:
            st.subheader("Create a New Meal")
            st.info("Create a meal by combining your dishes. Meals can be offered in chef events.")
            
            # Create form for new meal (only show if there are dishes)
            chef_dishes = fetch_chef_dishes()
            
            if not chef_dishes:
                st.warning("You need to create dishes first before you can create meals.")
                # Removing the non-functional button
            else:
                with st.form("create_meal_form"):
                    st.subheader("Meal Details")
                    
                    name = st.text_input("Meal Name", placeholder="Enter a name for your meal")
                    
                    description = st.text_area("Description", placeholder="Describe your meal in detail. Include details about ingredients, preparation method, and what makes it special.")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        meal_type = st.selectbox("Meal Type", options=["Breakfast", "Lunch", "Dinner"])
                        price = st.number_input("Price ($)", min_value=1.0, step=0.5, value=15.0,
                                               help="This is the base price for your meal. You can adjust pricing when creating events.")
                    
                    with col2:
                        start_date = st.date_input("Start Date (First Available)", min_value=datetime.now().date(),
                                                  help="The first date this meal will be available for events")
                        image_file = st.file_uploader("Upload Meal Image", type=["jpg", "jpeg", "png"],
                                                     help="A high-quality image of your meal helps attract customers")
                        
                        if image_file:
                            try:
                                st.image(image_file, caption="Preview", width=200)
                            except Exception as e:
                                st.warning("Unable to preview uploaded image.")
                                logging.warning(f"Image preview error: {str(e)}")
                    
                    st.markdown("---")
                    st.subheader("Dietary Preferences")
                    
                    # Fetch dietary preferences from the backend
                    dietary_preferences_data = fetch_dietary_preferences()
                    
                    if not dietary_preferences_data:
                        # Fall back to default preferences if API call fails
                        dietary_preferences_data = use_default_preferences()
                    
                    # Create a mapping of ID to name for display
                    dietary_prefs_map = {str(pref['id']): pref['name'] for pref in dietary_preferences_data}
                    
                    dietary_preferences = st.multiselect(
                        "Dietary Preferences", 
                        options=list(dietary_prefs_map.keys()),
                        format_func=lambda x: dietary_prefs_map.get(x, f"Preference {x}"),
                        help="Select any dietary preferences that apply to this meal"
                    )
                    
                    custom_prefs = st.text_input("Custom Dietary Preferences (Comma-separated)",
                                               help="Add any custom dietary preferences not listed above, separated by commas")
                    
                    st.markdown("---")
                    st.subheader("Dishes")
                    st.info("Add at least one dish to your meal")
                    
                    # Create options for the multiselect
                    dish_options = {str(dish['id']): dish['name'] for dish in chef_dishes}
                    
                    selected_dishes = st.multiselect(
                        "Select Dishes", 
                        options=list(dish_options.keys()),
                        format_func=lambda x: dish_options.get(x, f"Dish {x}"),
                        help="Select one or more dishes that make up this meal"
                    )
                    
                    # Add dish information with nutritional details
                    if selected_dishes:
                        st.caption("Selected Dishes:")
                        total_calories = 0
                        total_fat = 0
                        total_carbs = 0
                        total_protein = 0
                        
                        for dish_id in selected_dishes:
                            dish = next((d for d in chef_dishes if str(d['id']) == dish_id), None)
                            if dish:
                                st.markdown(f"- **{dish['name']}**")
                                
                                # List ingredients in the dish
                                if 'ingredients' in dish and dish['ingredients']:
                                    ingredients = dish['ingredients']
                                    if isinstance(ingredients, list) and len(ingredients) > 0:
                                        ing_names = []
                                        for ing in ingredients:
                                            if isinstance(ing, dict) and 'name' in ing:
                                                ing_names.append(ing['name'])
                                        
                                        if ing_names:
                                            st.markdown(f"  *Ingredients:* {', '.join(ing_names)}")
                                        
                                        # Calculate dish nutritional information
                                        dish_calories = sum(float(ing.get('calories', 0)) for ing in ingredients if isinstance(ing, dict))
                                        dish_fat = sum(float(ing.get('fat', 0)) for ing in ingredients if isinstance(ing, dict))
                                        dish_carbs = sum(float(ing.get('carbohydrates', 0)) for ing in ingredients if isinstance(ing, dict))
                                        dish_protein = sum(float(ing.get('protein', 0)) for ing in ingredients if isinstance(ing, dict))
                                        
                                        # Add to total meal nutrition
                                        total_calories += dish_calories
                                        total_fat += dish_fat
                                        total_carbs += dish_carbs
                                        total_protein += dish_protein
                                        
                                        # Display dish nutrition
                                        if dish_calories > 0:
                                            st.markdown(f"  *Nutrition:* {dish_calories:.0f} cal | {dish_fat:.1f}g fat | {dish_carbs:.1f}g carbs | {dish_protein:.1f}g protein")
                        
                        # Show total nutritional info for the meal
                        if total_calories > 0:
                            st.markdown("### Total Nutritional Information (per serving)")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Calories", f"{total_calories:.0f}")
                                st.metric("Fat", f"{total_fat:.1f}g")
                            with col2:
                                st.metric("Carbohydrates", f"{total_carbs:.1f}g")
                                st.metric("Protein", f"{total_protein:.1f}g")
                    
                    submit_button = st.form_submit_button("Create Meal")
                
                # Form validation and submission
                if submit_button:
                    # Show a spinner during processing
                    with st.spinner("Creating your meal..."):
                        # Validate required fields
                        validation_errors = []
                        
                        if not name:
                            validation_errors.append("Meal name is required")
                        
                        if not description:
                            validation_errors.append("Description is required")
                        
                        if not selected_dishes:
                            validation_errors.append("At least one dish is required")
                        
                        if validation_errors:
                            for error in validation_errors:
                                st.error(error)
                        else:
                            # Parse custom dietary preferences
                            custom_dietary_prefs = [pref.strip() for pref in custom_prefs.split(',') if pref.strip()] if custom_prefs else []
                            
                            # Prepare the data
                            data = {
                                'name': name,
                                'description': description,
                                'meal_type': meal_type,
                                'start_date': start_date.strftime('%Y-%m-%d'),
                                'price': price,
                                'dishes': selected_dishes,
                                'dietary_preferences': dietary_preferences,
                                'custom_dietary_preferences': custom_dietary_prefs
                            }
                            
                            # Submit the meal creation request
                            result = create_chef_meal(data, image_file)
                            
                            if result and result.get('status') == 'success':
                                st.success("Meal created successfully!")
                                
                                # Display the created meal details
                                if 'details' in result:
                                    meal_details = result['details']
                                    st.write("### Meal Details")
                                    st.write(f"**Name:** {meal_details.get('name')}")
                                    st.write(f"**Type:** {meal_details.get('meal_type')}")
                                    st.write(f"**Price:** ${meal_details.get('price')}")
                                
                                # Option to create another meal or go to create event
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("Create Another Meal"):
                                        st.rerun()
                                with col2:
                                    if st.button("Create an Event with this Meal"):
                                        # Set a session state variable to navigate to the create event tab
                                        st.session_state['navigate_to_create_event'] = True
                                        st.rerun()
                
                # Auto-navigate to Create Event tab if requested
                if st.session_state.get('navigate_to_create_event', False):
                    # Clear the flag
                    st.session_state['navigate_to_create_event'] = False
                    # This doesn't actually switch tabs - Streamlit doesn't support programmatic tab switching
                    # But it provides a clear button for the user to click
                    st.info("Click on the 'Create Event' tab to create an event with your new meal.")
                    if st.button("Go to Create Event Tab"):
                        pass  # This is just a visual cue
    
    # Tab for managing meals
    with meal_manage_tab:
        st.subheader("Manage Your Meals")
        st.info("View, edit, and manage the meals you've created.")
        
        # Fetch all meals created by the chef
        chef_meals_list = fetch_chef_meals()
        
        if not chef_meals_list:
            st.warning("You haven't created any meals yet. Use the 'Create Meal' tab to create your first meal.")
        else:
            # Display a clean interface for each meal
            for i, meal in enumerate(chef_meals_list):
                meal_id = meal.get('id')
                meal_name = meal.get('name', 'Unnamed Meal')
                meal_description = meal.get('description', '')
                meal_type = meal.get('meal_type', '')
                meal_price = meal.get('price', '0.00')
                
                # Use an expander for each meal to save space
                with st.expander(f"**{meal_name}**"):
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        # Show meal details
                        st.markdown(f"**Type:** {meal_type}")
                        st.markdown(f"**Price:** ${meal_price}")
                        
                        # Show description if it exists
                        if meal_description:
                            st.markdown(f"**Description:** {meal_description[:100]}..." if len(meal_description) > 100 else f"**Description:** {meal_description}")
                        
                        # Get dishes in this meal
                        if 'dishes' in meal and meal['dishes']:
                            dishes = meal['dishes']
                            if dishes:
                                dish_names = []
                                for dish in dishes:
                                    if isinstance(dish, dict) and 'name' in dish:
                                        dish_names.append(dish['name'])
                                    elif isinstance(dish, str):
                                        dish_names.append(dish)
                                
                                if dish_names:
                                    st.markdown(f"**Dishes:** {', '.join(dish_names)}")
                        
                        # Get dietary preferences
                        dietary_prefs = []
                        if 'dietary_preferences' in meal and meal['dietary_preferences']:
                            for pref in meal['dietary_preferences']:
                                if isinstance(pref, dict) and 'name' in pref:
                                    dietary_prefs.append(pref['name'])
                        
                        if 'custom_dietary_preferences' in meal and meal['custom_dietary_preferences']:
                            for pref in meal['custom_dietary_preferences']:
                                if isinstance(pref, dict) and 'name' in pref:
                                    dietary_prefs.append(pref['name'])
                        
                        if dietary_prefs:
                            st.markdown(f"**Dietary Preferences:** {', '.join(dietary_prefs)}")
                    
                    with col2:
                        # Show meal image if exists
                        if 'image' in meal and meal['image']:
                            try:
                                st.image(meal['image'], width=200)
                            except:
                                st.info("Image preview not available")
                    
                    with col3:
                        # Edit button
                        if st.button("✏️ Edit", key=f"edit_meal_{meal_id}"):
                            st.session_state['edit_meal_id'] = meal_id
                            st.rerun()
                        
                        # Delete button with confirmation
                        if st.button("🗑️ Delete", key=f"delete_meal_{meal_id}"):
                            st.session_state['delete_meal_id'] = meal_id
                            st.session_state['delete_meal_name'] = meal_name
                            st.rerun()
            
            # Handle edit meal
            if 'edit_meal_id' in st.session_state and st.session_state['edit_meal_id']:
                meal_id = st.session_state['edit_meal_id']
                
                # Get meal details for editing
                meal_details = get_chef_meal_details(meal_id)
                
                if meal_details:
                    st.markdown("---")
                    st.subheader(f"Edit Meal: {meal_details.get('name', '')}")
                    
                    with st.form("edit_meal_form"):
                        name = st.text_input("Meal Name", value=meal_details.get('name', ''))
                        description = st.text_area("Description", value=meal_details.get('description', ''))
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            meal_type_options = ["Breakfast", "Lunch", "Dinner"]
                            current_meal_type = meal_details.get('meal_type', 'Dinner')
                            meal_type = st.selectbox("Meal Type", options=meal_type_options, index=meal_type_options.index(current_meal_type) if current_meal_type in meal_type_options else 0)
                            
                            price = st.number_input("Price ($)", min_value=1.0, step=0.5, value=float(meal_details.get('price', 15.0)))
                        
                        with col2:
                            image_file = st.file_uploader("Meal Image (optional)", type=["jpg", "jpeg", "png"])
                            if 'image' in meal_details and meal_details['image']:
                                try:
                                    st.image(meal_details['image'], width=150, caption="Current image")
                                except Exception as e:
                                    st.warning("Unable to load image. It may be missing or inaccessible.")
                                    logging.warning(f"Image loading error: {str(e)}")
                        
                        # Get chef dishes for selection
                        chef_dishes = fetch_chef_dishes()
                        if chef_dishes:
                            # Create options for the multiselect
                            dish_options = {str(dish['id']): dish['name'] for dish in chef_dishes}
                            
                            # Get current dish IDs
                            current_dish_ids = []
                            if 'dishes' in meal_details and meal_details['dishes']:
                                for dish in meal_details['dishes']:
                                    if isinstance(dish, dict) and 'id' in dish:
                                        current_dish_ids.append(str(dish['id']))
                            
                            selected_dishes = st.multiselect(
                                "Select Dishes", 
                                options=list(dish_options.keys()),
                                default=current_dish_ids,
                                format_func=lambda x: dish_options.get(x, f"Dish {x}"),
                                help="Select one or more dishes that make up this meal"
                            )
                            
                            # Get dietary preferences for selection
                            dietary_prefs = fetch_dietary_preferences()
                            if dietary_prefs:
                                # Create options for the multiselect
                                pref_options = {str(pref['id']): pref['name'] for pref in dietary_prefs}
                                
                                # Get current dietary preference IDs
                                current_pref_ids = []
                                if 'dietary_preferences' in meal_details and meal_details['dietary_preferences']:
                                    for pref in meal_details['dietary_preferences']:
                                        if isinstance(pref, dict) and 'id' in pref:
                                            current_pref_ids.append(str(pref['id']))
                                
                                dietary_preferences = st.multiselect(
                                    "Dietary Preferences", 
                                    options=list(pref_options.keys()),
                                    default=current_pref_ids,
                                    format_func=lambda x: pref_options.get(x, f"Preference {x}"),
                                    help="Select applicable dietary preferences for this meal"
                                )
                                
                                # Get current custom dietary preferences
                                current_custom_prefs = []
                                if 'custom_dietary_preferences' in meal_details and meal_details['custom_dietary_preferences']:
                                    for pref in meal_details['custom_dietary_preferences']:
                                        if isinstance(pref, dict) and 'name' in pref:
                                            current_custom_prefs.append(pref['name'])
                                
                                custom_prefs = st.text_input(
                                    "Custom Dietary Preferences (comma separated)", 
                                    value=', '.join(current_custom_prefs),
                                    help="Add your own dietary preferences not listed above (separate with commas)"
                                )
                            else:
                                dietary_preferences = []
                                custom_prefs = st.text_input(
                                    "Custom Dietary Preferences (comma separated)", 
                                    help="Add dietary preferences (separate with commas)"
                                )
                        else:
                            st.warning("You need to create dishes before you can update this meal.")
                            selected_dishes = []
                            dietary_preferences = []
                            custom_prefs = ""
                        
                        update_submit = st.form_submit_button("Update Meal")
                    
                    if update_submit:
                        # Show a spinner during processing
                        with st.spinner("Updating your meal..."):
                            # Validate required fields
                            validation_errors = []
                            
                            if not name:
                                validation_errors.append("Meal name is required")
                            
                            if not description:
                                validation_errors.append("Description is required")
                            
                            if not selected_dishes:
                                validation_errors.append("At least one dish is required")
                            
                            if validation_errors:
                                for error in validation_errors:
                                    st.error(error)
                            else:
                                # Parse custom dietary preferences
                                custom_dietary_prefs = [pref.strip() for pref in custom_prefs.split(',') if pref.strip()] if custom_prefs else []
                                
                                # Prepare the data
                                data = {
                                    'name': name,
                                    'description': description,
                                    'meal_type': meal_type,
                                    'price': price,
                                    'dishes': selected_dishes,
                                    'dietary_preferences': dietary_preferences,
                                    'custom_dietary_preferences': custom_dietary_prefs
                                }
                                
                                # Submit the meal update request
                                result = update_chef_meal(meal_id, data, image_file)
                                if result:
                                    st.success("Meal updated successfully!")
                                    # Clear session state
                                    st.session_state.pop('edit_meal_id', None)
                                    st.rerun()
                else:
                    st.error("Failed to load meal details for editing")
                    # Clear session state
                    st.session_state.pop('edit_meal_id', None)
            
            # Handle delete meal confirmation
            if 'delete_meal_id' in st.session_state and st.session_state['delete_meal_id']:
                meal_id = st.session_state['delete_meal_id']
                meal_name = st.session_state.get('delete_meal_name', 'this meal')
                
                st.markdown("---")
                st.subheader(f"Confirm Deletion: {meal_name}")
                st.warning(f"Are you sure you want to delete '{meal_name}'? This action cannot be undone.")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Yes, Delete"):
                        if delete_chef_meal(meal_id):
                            # Reset session state
                            st.session_state.pop('delete_meal_id', None)
                            st.session_state.pop('delete_meal_name', None)
                            st.success(f"'{meal_name}' has been deleted.")
                            st.rerun()
                
                with col2:
                    if st.button("Cancel"):
                        # Reset session state
                        st.session_state.pop('delete_meal_id', None)
                        st.session_state.pop('delete_meal_name', None)
                        st.rerun()
    
    # Tab 5: Create Event (previously Tab 4)
    with tab5:
        st.header("Create a Meal Event")
        
        # Check if Stripe account is active
        stripe_status = check_stripe_account_status()
        if not stripe_status.get('is_active', False):
            st.warning("You need to set up your Stripe account before creating meal events.")
            if st.button("Set Up Stripe Account", key="setup_stripe_create"):
                stripe_url = create_stripe_account()
                if stripe_url:
                    st.success("Stripe account creation initiated. Click the link below to continue:")
                    st.markdown(f"[Complete Stripe Onboarding]({stripe_url})")
            return
        
        # Fetch chef's meals
        meals = fetch_chef_meals()
        
        if not meals:
            st.warning("You need to create meals before you can create meal events.")
            return
        
        # Create form for new meal event
        with st.form("create_meal_event_form"):
            meal_options = {m['id']: m['name'] for m in meals}
            meal_id = st.selectbox("Select Meal", options=list(meal_options.keys()), format_func=lambda x: meal_options[x])
            
            col1, col2 = st.columns(2)
            
            with col1:
                event_date = st.date_input("Event Date", min_value=datetime.now().date() + timedelta(days=1))
                event_time = st.time_input("Event Time", value=datetime.now().time().replace(hour=18, minute=0))
                # Allow any date to be selected with minimal constraints
                cutoff_date = st.date_input("Order Cutoff Date", min_value=datetime.now().date())
                order_cutoff_time = st.time_input("Order Cutoff Time", value=datetime.now().time().replace(hour=12, minute=0))
            
            with col2:
                base_price = st.number_input("Base Price ($)", min_value=5.0, step=1.0, value=15.0)
                min_price = st.number_input("Minimum Price ($)", min_value=1.0, step=1.0, value=max(5.0, base_price * 0.7), 
                                          help="The lowest price you'll accept per meal as more people order. Cannot go below $1.")
                max_orders = st.number_input("Maximum Orders", min_value=1, step=1, value=10)
                min_orders = st.number_input("Minimum Orders", min_value=1, max_value=max_orders, step=1, value=3)
            
            description = st.text_area("Event Description", placeholder="Describe your meal event...")
            special_instructions = st.text_area("Special Instructions (Optional)", placeholder="Any special instructions for customers...")
            
            submit_button = st.form_submit_button("Create Meal Event")
        
        if submit_button:
            # Format the date and cutoff time
            cutoff_datetime = datetime.combine(cutoff_date, order_cutoff_time)
            
            # Prepare the data
            data = {
                'meal': meal_id,
                'event_date': event_date.strftime('%Y-%m-%d'),
                'event_time': event_time.strftime('%H:%M'),
                'order_cutoff_time': cutoff_datetime.strftime('%Y-%m-%d %H:%M'),
                'base_price': base_price,
                'min_price': min_price,
                'max_orders': max_orders,
                'min_orders': min_orders,
                'description': description,
                'special_instructions': special_instructions
            }
            
            # Create the meal event
            result = create_chef_meal_event(data)
            
            if result:
                if 'error' in result:
                    st.error(result['error'])
                else:
                    st.success("Meal event created successfully!")
                    st.rerun()

def create_chef_meal(data, image_file=None):
    """
    Create a new chef meal by calling the create-chef-meal API endpoint.
    If an image file is provided, it will be uploaded alongside the meal data.
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        
        # Prepare the request based on whether we have an image file
        if image_file is not None:
            # For file uploads, we need to use multipart/form-data
            files = {'image': image_file}
            
            # Convert list fields to JSON strings for multipart form submission
            form_data = data.copy()
            if 'dishes' in form_data and isinstance(form_data['dishes'], list):
                form_data['dishes'] = json.dumps(form_data['dishes'])
            if 'dietary_preferences' in form_data and isinstance(form_data['dietary_preferences'], list):
                form_data['dietary_preferences'] = json.dumps(form_data['dietary_preferences'])
            if 'custom_dietary_preferences' in form_data and isinstance(form_data['custom_dietary_preferences'], list):
                form_data['custom_dietary_preferences'] = json.dumps(form_data['custom_dietary_preferences'])
            
            response = api_call_with_refresh(
                url=f"{os.getenv('DJANGO_URL')}/meals/api/chef/meals/",
                method='post',
                headers=headers,
                data=form_data,
                files=files
            )
        else:
            # No image, regular JSON submission
            response = api_call_with_refresh(
                url=f"{os.getenv('DJANGO_URL')}/meals/api/chef/meals/",
                method='post',
                headers=headers,
                data=data
            )
        
        if response and response.status_code in [200, 201]:
            logging.info(f"Meal creation successful: {response.json()}")
            result = response.json()
            if 'status' in result and result['status'] == 'success':
                st.success(result.get('message', 'Meal created successfully!'))
                return result.get('details', result)
            return result
        else:
            if response:
                error_msg = f"Error creating meal: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg = error_data['message']
                    elif 'error' in error_data:
                        error_msg = error_data['error']
                    elif 'details' in error_data and isinstance(error_data['details'], dict):
                        # Format field-specific errors
                        field_errors = []
                        for field, errors in error_data['details'].items():
                            if isinstance(errors, list):
                                error_text = ', '.join(errors)
                                field_errors.append(f"{field}: {error_text}")
                            else:
                                field_errors.append(f"{field}: {errors}")
                        if field_errors:
                            error_msg = 'Validation errors: ' + '; '.join(field_errors)
                except:
                    error_msg += f" - {response.text}"
                
                st.error(error_msg)
                logging.error(f"Meal creation failed: {error_msg}")
            else:
                st.error("Failed to create meal - no response from server")
                logging.error("Meal creation failed: No response from server")
            return None
    except Exception as e:
        error_msg = str(e)
        st.error(f"Error creating meal: {error_msg}")
        logging.error(f"Exception in create_chef_meal: {error_msg}", exc_info=True)
        return None

def update_chef_meal(meal_id, data, image_file=None):
    """
    Update an existing chef meal.
    If an image file is provided, it will be uploaded alongside the updated meal data.
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        
        # Prepare the request based on whether we have an image file
        if image_file is not None:
            # For file uploads, we need to use multipart/form-data
            files = {'image': image_file}
            
            # Convert list fields to JSON strings for multipart form submission
            form_data = data.copy()
            if 'dishes' in form_data and isinstance(form_data['dishes'], list):
                form_data['dishes'] = json.dumps(form_data['dishes'])
            if 'dietary_preferences' in form_data and isinstance(form_data['dietary_preferences'], list):
                form_data['dietary_preferences'] = json.dumps(form_data['dietary_preferences'])
            if 'custom_dietary_preferences' in form_data and isinstance(form_data['custom_dietary_preferences'], list):
                form_data['custom_dietary_preferences'] = json.dumps(form_data['custom_dietary_preferences'])
            
            response = api_call_with_refresh(
                url=f"{os.getenv('DJANGO_URL')}/meals/api/chef/meals/{meal_id}/update/",
                method='patch',
                headers=headers,
                data=form_data,
                files=files
            )
        else:
            # No image, regular JSON submission
            response = api_call_with_refresh(
                url=f"{os.getenv('DJANGO_URL')}/meals/api/chef/meals/{meal_id}/update/",
                method='patch',
                headers=headers,
                data=data
            )
        
        if response and response.status_code in [200, 201]:
            logging.info(f"Meal update successful: {response.json()}")
            result = response.json()
            if 'status' in result and result['status'] == 'success':
                st.success(result.get('message', 'Meal updated successfully!'))
                return result.get('details', result)
            return result
        else:
            if response:
                error_msg = f"Error updating meal: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg = error_data['message']
                    elif 'error' in error_data:
                        error_msg = error_data['error']
                    elif 'details' in error_data and isinstance(error_data['details'], dict):
                        # Format field-specific errors
                        field_errors = []
                        for field, errors in error_data['details'].items():
                            if isinstance(errors, list):
                                error_text = ', '.join(errors)
                                field_errors.append(f"{field}: {error_text}")
                            else:
                                field_errors.append(f"{field}: {errors}")
                        if field_errors:
                            error_msg = 'Validation errors: ' + '; '.join(field_errors)
                except:
                    error_msg += f" - {response.text}"
                
                st.error(error_msg)
                logging.error(f"Meal update failed: {error_msg}")
            else:
                st.error("Failed to update meal - no response from server")
                logging.error("Meal update failed: No response from server")
            return None
    except Exception as e:
        error_msg = str(e)
        st.error(f"Error updating meal: {error_msg}")
        logging.error(f"Exception in update_chef_meal: {error_msg}", exc_info=True)
        return None

def delete_chef_meal(meal_id):
    """
    Delete a chef meal.
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/chef/meals/{meal_id}/",
            method='delete',
            headers=headers
        )
        
        if response and response.status_code in [200, 204]:
            try:
                result = response.json()
                message = result.get('message', 'Meal deleted successfully!')
            except:
                message = 'Meal deleted successfully!'
            
            st.success(message)
            return True
        else:
            if response:
                error_msg = "Error deleting meal"
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg = error_data['message']
                except:
                    error_msg = f"Error deleting meal: Status code {response.status_code}"
                
                st.error(error_msg)
                logging.error(f"Meal deletion failed: {error_msg}")
            else:
                st.error("Failed to delete meal - no response from server")
                logging.error("Meal deletion failed: No response from server")
            return False
    except Exception as e:
        error_msg = str(e)
        st.error(f"Error deleting meal: {error_msg}")
        logging.error(f"Exception in delete_chef_meal: {error_msg}", exc_info=True)
        return False

def get_chef_meal_details(meal_id):
    """
    Get details of a specific chef meal.
    """
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/chef/meals/{meal_id}/",
            method='get',
            headers=headers
        )
        
        if response and response.status_code == 200:
            result = response.json()
            if 'status' in result and result['status'] == 'success':
                return result.get('details', {})
            return result
        else:
            if response:
                logging.error(f"Error fetching meal details: {response.status_code}, {response.text}")
            return None
    except Exception as e:
        logging.error(f"Exception in get_chef_meal_details: {str(e)}", exc_info=True)
        return None

# Call the chef_meals function inside a try/except block (consistent with other views)
try:
    chef_meals()
except Exception as e:
    st.error("We're experiencing technical difficulties loading the Chef Meals page. Our team has been notified.")
    logging.error(f"An error occurred in chef_meals: {str(e)}")
    logging.error(traceback.format_exc())