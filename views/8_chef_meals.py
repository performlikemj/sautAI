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
from utils import api_call_with_refresh, login_form, toggle_chef_mode, is_user_authenticated, validate_input, footer

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
        else:
            # Use development mode to return mock data if the API fails
            dev_mode = st.session_state.get('dev_mode', False)
            if dev_mode:
                logging.warning("Using mock chef status data (dev mode)")
                return {'is_chef': False, 'has_pending_request': False}
            
            logging.error(f"Failed to check chef status. Status: {response.status_code if response else 'No response'}")
            return {'is_chef': False, 'has_pending_request': False}
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
        print(f"Stripe account link data: {data}")
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/stripe-account-link/",
            method='post',
            data=data,
            headers=headers
        )
        print(f"Stripe account link response: {response}")
        if response and response.status_code == 200:
            data = response.json()
            print(f"Stripe account link data: {data}")
            return data.get('url')
        else:
            # Use development mode to return mock data if the API fails
            dev_mode = st.session_state.get('dev_mode', False)
            if dev_mode:
                logging.warning("Using mock Stripe account link (dev mode)")
                return "https://example.com/mock-stripe-onboarding"
                
            logging.error(f"Failed to create Stripe account link. Status: {response.status_code if response else 'No response'}")
            if response:
                print(f"Stripe account link error: {response.json()}")
            st.error("Failed to create Stripe account link")
            return None
    except Exception as e:
        # Use development mode to return mock data if the API fails
        dev_mode = st.session_state.get('dev_mode', False)
        if dev_mode:
            logging.warning("Using mock Stripe account link (dev mode)")
            return "https://example.com/mock-stripe-onboarding"
            
        st.error(f"Error creating Stripe account: {str(e)}")
        logging.error(f"Error creating Stripe account: {str(e)}")
        logging.error(traceback.format_exc())
        return None

# Function to check Stripe account status
def check_stripe_account_status():
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/stripe-account-status/",
            method='get',
            headers=headers
        )
        
        if response and response.status_code == 200:
            return response.json()
        else:
            # Use development mode to return mock data if the API fails
            dev_mode = st.session_state.get('dev_mode', False)
            if dev_mode:
                logging.warning("Using mock Stripe account status data (dev mode)")
                return {'has_account': True, 'is_active': True}
            
            logging.error(f"Failed to check Stripe account status. Status: {response.status_code if response else 'No response'}")
            st.error("Failed to check Stripe account status")
            return {'has_account': False}
    except Exception as e:
        # Use development mode to return mock data if the API fails
        dev_mode = st.session_state.get('dev_mode', False)
        if dev_mode:
            logging.warning("Using mock Stripe account status data (dev mode)")
            return {'has_account': True, 'is_active': True}
            
        st.error(f"Error checking Stripe account status: {str(e)}")
        logging.error(f"Error checking Stripe account status: {str(e)}")
        logging.error(traceback.format_exc())
        return {'has_account': False}

# Function to get chef dashboard stats
def get_chef_dashboard_stats():
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        url = f"{os.getenv('DJANGO_URL')}/meals/api/chef-dashboard-stats/"
        logging.info(f"Fetching chef dashboard stats from: {url}")
        
        response = api_call_with_refresh(
            url=url,
            method='get',
            headers=headers
        )
        
        if response and response.status_code == 200:
            data = response.json()
            logging.info(f"Dashboard stats API response type: {type(data)}")
            logging.info(f"Dashboard stats API response content: {data}")
            
            if isinstance(data, dict):
                logging.info(f"Dashboard stats keys: {data.keys()}")
            
            return data
        else:
            # Use development mode to return mock data if the API fails
            dev_mode = st.session_state.get('dev_mode', False)
            if dev_mode:
                logging.warning("Using mock dashboard stats data (dev mode)")
                return {
                    'upcoming_events_count': 2,
                    'active_orders_count': 5,
                    'review_count': 12,
                    'avg_rating': 4.7,
                    'revenue_this_month': 350.00
                }
                
            logging.error(f"Failed to fetch dashboard statistics. Status: {response.status_code if response else 'No response'}")
            st.error("Failed to fetch dashboard statistics")
            return {}
    except Exception as e:
        # Use development mode to return mock data if the API fails
        dev_mode = st.session_state.get('dev_mode', False)
        if dev_mode:
            logging.warning("Using mock dashboard stats data (dev mode)")
            return {
                'upcoming_events_count': 2,
                'active_orders_count': 5,
                'review_count': 12,
                'avg_rating': 4.7,
                'revenue_this_month': 350.00
            }
            
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
        print(f"Chef meal events response: {response}")
        if response and response.status_code == 200:
            data = response.json()
            print(f"Chef meal events response: {data}")
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
            # Use development mode to return mock data if the API fails
            dev_mode = st.session_state.get('dev_mode', False)
            if dev_mode:
                logging.warning("Using mock meal events data (dev mode)")
                tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
                
                # Create mock event data
                mock_events = [
                    {
                        'id': 1,
                        'meal': {'id': 1, 'name': 'Mock Meal 1', 'description': 'This is a mock meal for testing'},
                        'event_date': tomorrow,
                        'event_time': '18:00',
                        'order_cutoff_time': f"{tomorrow}T12:00:00Z",
                        'base_price': '25.00',
                        'current_price': '22.00',
                        'max_orders': 10,
                        'orders_count': 3,
                        'status': 'active',
                        'description': 'Mock event for tomorrow',
                        'special_instructions': 'These are mock instructions'
                    },
                    {
                        'id': 2,
                        'meal': {'id': 2, 'name': 'Mock Meal 2', 'description': 'Another mock meal for testing'},
                        'event_date': next_week,
                        'event_time': '19:00',
                        'order_cutoff_time': f"{next_week}T12:00:00Z",
                        'base_price': '30.00',
                        'current_price': '27.50',
                        'max_orders': 15,
                        'orders_count': 5,
                        'status': 'active',
                        'description': 'Mock event for next week',
                        'special_instructions': ''
                    }
                ]
                return mock_events
                
            st.error("Failed to fetch chef meal events")
            return []
    except Exception as e:
        # Use development mode to return mock data if the API fails
        dev_mode = st.session_state.get('dev_mode', False)
        if dev_mode:
            logging.warning("Using mock meal events data (dev mode)")
            tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            
            # Create mock event data
            mock_events = [
                {
                    'id': 1,
                    'meal': {'id': 1, 'name': 'Mock Meal 1', 'description': 'This is a mock meal for testing'},
                    'event_date': tomorrow,
                    'event_time': '18:00',
                    'order_cutoff_time': f"{tomorrow}T12:00:00Z",
                    'base_price': '25.00',
                    'current_price': '22.00',
                    'max_orders': 10,
                    'orders_count': 3,
                    'status': 'active',
                    'description': 'Mock event for tomorrow',
                    'special_instructions': 'These are mock instructions'
                },
                {
                    'id': 2,
                    'meal': {'id': 2, 'name': 'Mock Meal 2', 'description': 'Another mock meal for testing'},
                    'event_date': next_week,
                    'event_time': '19:00',
                    'order_cutoff_time': f"{next_week}T12:00:00Z",
                    'base_price': '30.00',
                    'current_price': '27.50',
                    'max_orders': 15,
                    'orders_count': 5,
                    'status': 'active',
                    'description': 'Mock event for next week',
                    'special_instructions': ''
                }
            ]
            return mock_events
            
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
            logging.info(f"Chef meal orders API response type: {type(data)}")
            logging.info(f"Chef meal orders API response content: {data}")
            
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

# Function to process payment for a chef meal order
def process_payment(order_id, token):
    try:
        headers = {'Authorization': f'Bearer {st.session_state.user_info["access"]}'}
        data = {'token': token}
        response = api_call_with_refresh(
            url=f"{os.getenv('DJANGO_URL')}/meals/api/process-chef-meal-payment/{order_id}/",
            method='post',
            headers=headers,
            data=data
        )
        
        if response and response.status_code == 200:
            return response.json()
        else:
            if response:
                error_message = response.json().get('error', 'Payment processing failed')
                st.error(error_message)
            else:
                st.error("Payment processing failed")
            return None
    except Exception as e:
        st.error(f"Error processing payment: {str(e)}")
        logging.error(f"Error processing payment: {str(e)}")
        logging.error(traceback.format_exc())
        return None

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
            logging.info(f"Chef meals API response type: {type(data)}")
            logging.info(f"Chef meals API response content: {data}")
            
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
        
        print(f"Dish creation response: {response}")
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
            
            # In development mode, return mock data
            if st.session_state.get('dev_mode', False):
                logging.warning("Using mock dish data (dev mode)")
                return [
                    {'id': 1, 'name': 'Appetizer Sample', 'description': 'A sample appetizer', 'featured': False},
                    {'id': 2, 'name': 'Main Course Sample', 'description': 'A sample main course', 'featured': True},
                    {'id': 3, 'name': 'Dessert Sample', 'description': 'A sample dessert', 'featured': False}
                ]
            return []
    except Exception as e:
        logging.error(f"Error fetching chef dishes: {str(e)}")
        logging.error(traceback.format_exc())
        
        # In development mode, return mock data
        if st.session_state.get('dev_mode', False):
            logging.warning("Using mock dish data (dev mode)")
            return [
                {'id': 1, 'name': 'Appetizer Sample', 'description': 'A sample appetizer', 'featured': False},
                {'id': 2, 'name': 'Main Course Sample', 'description': 'A sample main course', 'featured': True},
                {'id': 3, 'name': 'Dessert Sample', 'description': 'A sample dessert', 'featured': False}
            ]
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
            
            # In development mode, return mock data
            if st.session_state.get('dev_mode', False):
                logging.warning("Using mock ingredient data (dev mode)")
                return [
                    {'id': 1, 'name': 'Chicken', 'calories': 165, 'fat': 3.6, 'carbohydrates': 0, 'protein': 31},
                    {'id': 2, 'name': 'Rice', 'calories': 130, 'fat': 0.3, 'carbohydrates': 28, 'protein': 2.7},
                    {'id': 3, 'name': 'Tomatoes', 'calories': 18, 'fat': 0.2, 'carbohydrates': 3.9, 'protein': 0.9}
                ]
            return []
    except Exception as e:
        logging.error(f"Error fetching chef ingredients: {str(e)}")
        logging.error(traceback.format_exc())
        
        # In development mode, return mock data
        if st.session_state.get('dev_mode', False):
            logging.warning("Using mock ingredient data (dev mode)")
            return [
                {'id': 1, 'name': 'Chicken', 'calories': 165, 'fat': 3.6, 'carbohydrates': 0, 'protein': 31},
                {'id': 2, 'name': 'Rice', 'calories': 130, 'fat': 0.3, 'carbohydrates': 28, 'protein': 2.7},
                {'id': 3, 'name': 'Tomatoes', 'calories': 18, 'fat': 0.2, 'carbohydrates': 3.9, 'protein': 0.9}
            ]
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

    # Add development mode toggle in the sidebar
    with st.sidebar:
        st.markdown("---")
        st.markdown("### Developer Options")
        dev_mode = st.toggle("Development Mode", 
                           value=st.session_state.get('dev_mode', False),
                           help="Enable mock data when API endpoints are not available")
        
        # Update session state
        st.session_state['dev_mode'] = dev_mode
        
        if dev_mode:
            st.info("Development mode enabled. Using mock data for missing API endpoints.")
    
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
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Dashboard", "My Meal Events", "Received Orders", "Create Meal", "Create Event"])
    
    # Tab 1: Chef Dashboard
    with tab1:
        st.header("Chef Dashboard")
        
        # Check Stripe account status
        stripe_status = check_stripe_account_status()
        print(f"Stripe status: {stripe_status}")
        print(f"Stripe status has_account: {stripe_status.get('has_account', False)}")
        print(f"Stripe status is_active: {stripe_status.get('is_active', False)}")
        if not stripe_status.get('has_account', False):
            st.warning("You need to set up your Stripe account to receive payments for your meal events.")
            if st.button("Set Up Stripe Account"):
                stripe_url = create_stripe_account()
                if stripe_url:
                    st.success("Stripe account creation initiated. Click the link below to continue:")
                    st.markdown(f"[Complete Stripe Onboarding]({stripe_url})")
                    st.info("After completing the onboarding, return to this page.")
        elif not stripe_status.get('is_active', False):
            st.warning("Your Stripe account is not fully set up. Please complete the onboarding process.")
            if st.button("Complete Stripe Account Setup"):
                stripe_url = create_stripe_account()
                if stripe_url:
                    st.success("Click the link below to complete your Stripe account setup:")
                    st.markdown(f"[Complete Stripe Onboarding]({stripe_url})")
                    st.info("After completing the onboarding, return to this page.")
        elif stripe_status.get('disabled_reason', None):
            st.warning(f"There's an issue with your Stripe account: {stripe_status.get('disabled_reason', 'Unknown reason')}")
            if st.button("Update Stripe Account"):
                stripe_url = create_stripe_account()
                if stripe_url:
                    st.success("Click the link below to update your Stripe account:")
                    st.markdown(f"[Update Stripe Account]({stripe_url})")
        else:
            st.success("Your Stripe account is active and ready to receive payments!")
        
        # Display dashboard statistics
        stats = get_chef_dashboard_stats()
        
        if stats:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Upcoming Events", stats.get('upcoming_events_count', 0))
            
            with col2:
                st.metric("Active Orders", stats.get('active_orders_count', 0))
            
            with col3:
                st.metric("Reviews", stats.get('review_count', 0))
            
            with col4:
                st.metric("Average Rating", f"{float(stats.get('avg_rating', 0)):.1f}★")
            
            st.subheader("Revenue")
            st.info(f"Monthly Revenue: {format_currency(stats.get('revenue_this_month', 0))}")
            
            # Add a placeholder for future charts
            st.subheader("Order History")
            st.info("Detailed analytics coming soon!")
    
    # Tab 2: My Meal Events
    with tab2:
        st.header("My Meal Events")
        
        # Add refresh button that will trigger a rerun when clicked
        refresh_clicked = st.button("Refresh Events", key="refresh_events")
        if refresh_clicked:
            st.rerun()  # This will rerun the app and fetch fresh data
            
        # Fetch chef's meal events
        events = fetch_chef_meal_events(my_events=True)
        
        # Debug information
        if dev_mode:
            st.info(f"Found {len(events)} events from the API")
            if len(events) == 0:
                # Show current dashboard stats to compare
                stats = get_chef_dashboard_stats()
                st.write("Dashboard shows:")
                st.write(f"- Upcoming Events: {stats.get('upcoming_events_count', 0)}")
        
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
                                
                                # Cancel button if event is still upcoming
                                if event['status'] not in ['cancelled', 'completed']:
                                    if st.button(f"Cancel Event", key=f"cancel_{event['id']}"):
                                        reason = st.text_area("Reason for cancellation", key=f"reason_{event['id']}")
                                        if st.button(f"Confirm Cancellation", key=f"confirm_{event['id']}"):
                                            if cancel_chef_meal_event(event['id'], reason):
                                                st.success("Event cancelled successfully!")
                                                st.rerun()
                            
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
        
        if orders:
            # Add detailed logging before processing orders
            logging.info(f"Processing orders of type: {type(orders)}")
            
            try:
                # Split into active and past orders
                active_orders = [o for o in orders if o['status'] in ['placed', 'confirmed']]
                logging.info(f"Active orders: {len(active_orders)}")
                
                completed_orders = [o for o in orders if o['status'] == 'completed']
                logging.info(f"Completed orders: {len(completed_orders)}")
                
                cancelled_orders = [o for o in orders if o['status'] in ['cancelled', 'refunded']]
                logging.info(f"Cancelled orders: {len(cancelled_orders)}")
                
                # Display active orders
                if active_orders:
                    st.subheader("Active Orders")
                    for order in active_orders:
                        with st.expander(f"Order #{order['id']} - {order['customer']['username']}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown(f"**Meal:** {order['meal_event']['meal']['name']}")
                                st.markdown(f"**Event Date:** {format_date(order['meal_event']['event_date'])}")
                                st.markdown(f"**Quantity:** {order['quantity']}")
                                st.markdown(f"**Price Paid:** {format_currency(float(order['price_paid']) * order['quantity'])}")
                            
                            with col2:
                                st.markdown(f"**Status:** {order['status'].capitalize()}")
                                st.markdown(f"**Order Date:** {format_datetime(order['created_at'])}")
                                
                                # Button to mark as completed if event date has passed
                                event_date = datetime.strptime(order['meal_event']['event_date'], '%Y-%m-%d').date()
                                if order['status'] == 'confirmed' and event_date <= datetime.now().date():
                                    if st.button(f"Mark as Completed", key=f"complete_{order['id']}"):
                                        # Implement the completion logic here
                                        st.success("Order marked as completed!")
                                        st.rerun()
                        
                            if order['special_requests']:
                                st.markdown(f"**Special Requests:** {order['special_requests']}")
                else:
                    st.info("You don't have any active orders.")
                
                # Display completed orders in a table
                if completed_orders:
                    st.subheader("Completed Orders")
                    completed_df = pd.DataFrame([
                        {
                            'Order Date': format_datetime(o['created_at']),
                            'Customer': o['customer']['username'],
                            'Meal': o['meal_event']['meal']['name'],
                            'Quantity': o['quantity'],
                            'Total': format_currency(float(o['price_paid']) * o['quantity'])
                        } for o in completed_orders
                    ])
                    
                    st.dataframe(completed_df)
                
                # Display cancelled orders in a table
                if cancelled_orders:
                    st.subheader("Cancelled Orders")
                    cancelled_df = pd.DataFrame([
                        {
                            'Order Date': format_datetime(o['created_at']),
                            'Customer': o['customer']['username'],
                            'Meal': o['meal_event']['meal']['name'],
                            'Status': o['status'].capitalize(),
                            'Refunded': 'Yes' if o['status'] == 'refunded' else 'No'
                        } for o in cancelled_orders
                    ])
                    
                    st.dataframe(cancelled_df)
            except Exception as e:
                st.error(f"Error processing orders: {str(e)}")
                logging.error(f"Error processing orders: {str(e)}")
                logging.error(traceback.format_exc())
        else:
            st.info("You haven't received any orders yet.")
    
    # Tab 4: Create Meal
    with tab4:
        st.header("Create a Meal")
        
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
                            st.image(image_file, caption="Preview", width=200)
                    
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
                                st.image(meal_details['image'], width=150, caption="Current image")
                        
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
                min_price = st.number_input("Minimum Price ($)", min_value=1.0, max_value=base_price, step=1.0, value=max(5.0, base_price * 0.7))
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
                url=f"{os.getenv('DJANGO_URL')}/meals/api/chef/meals/{meal_id}/",
                method='patch',
                headers=headers,
                data=form_data,
                files=files
            )
        else:
            # No image, regular JSON submission
            response = api_call_with_refresh(
                url=f"{os.getenv('DJANGO_URL')}/meals/api/chef/meals/{meal_id}/",
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
    logging.error(f"An error occurred: {str(e)}")
    logging.error(traceback.format_exc())
    st.error("An unexpected error occurred. Please try again later.")
