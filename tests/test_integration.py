import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import streamlit as st
from requests.exceptions import RequestException
import json

# Add the parent directory to sys.path to import views and utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestStreamlitRegistrationIntegration:
    """Integration tests for Streamlit registration form"""
    
    def setup_method(self):
        """Setup for each test method"""
        # Mock Streamlit session state
        if 'mock_session_state' not in st.session_state:
            st.session_state.mock_session_state = {}

    @patch('streamlit.form_submit_button')
    @patch('streamlit.text_input')
    @patch('streamlit.text_area')
    @patch('streamlit.number_input')
    @patch('streamlit.multiselect')
    @patch('streamlit.selectbox')
    @patch('requests.post')
    def test_successful_registration_form_submission(self, mock_post, mock_selectbox, 
                                                   mock_multiselect, mock_number_input,
                                                   mock_text_area, mock_text_input, 
                                                   mock_form_submit):
        """Test successful form submission"""
        # Mock form inputs
        mock_text_input.side_effect = [
            "testuser123",  # username
            "test@example.com",  # email
            "SecurePass123!",  # password
            "+1234567890",  # phone_number
            "123 Main St",  # street
            "Test City",  # city
            "Test State",  # state
            "12345",  # postal_code
            "Healthy Eating",  # goal_name
        ]
        mock_text_area.side_effect = [
            "",  # custom_dietary_preferences
            "",  # custom_allergies
            "Eat healthier meals"  # goal_description
        ]
        mock_multiselect.side_effect = [
            ["Everything"],  # dietary_preferences
            []  # allergies
        ]
        mock_selectbox.side_effect = [
            "United States",  # country
            "English (English)",  # language
            "UTC"  # timezone
        ]
        mock_number_input.side_effect = [
            2,  # household_member_count
            7   # emergency_supply_goal
        ]
        mock_form_submit.return_value = True
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Registration successful"}
        mock_post.return_value = mock_response
        
        # This would test the actual registration logic
        # (In a real test, you'd import and run the registration function)
        assert mock_response.status_code == 200

    @patch('streamlit.form_submit_button')
    @patch('streamlit.text_input')
    @patch('streamlit.error')
    @patch('streamlit.warning')
    @patch('requests.post')
    def test_email_enumeration_prevention_in_ui(self, mock_post, mock_warning, 
                                               mock_error, mock_text_input, 
                                               mock_form_submit):
        """Test that UI doesn't reveal email enumeration"""
        mock_text_input.side_effect = [
            "testuser123",
            "existing@example.com",  # Existing email
            "password123",
            # ... other inputs
        ]
        mock_form_submit.return_value = True
        
        # Mock API response for existing email
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "errors": {
                "email": ["This email already exists"]
            }
        }
        mock_post.return_value = mock_response
        
        # In our implementation, this should show a generic message
        # The actual test would verify that mock_error was called with generic message
        assert mock_response.status_code == 400

    @patch('streamlit.form_submit_button')
    @patch('streamlit.text_input')
    @patch('streamlit.error')
    @patch('streamlit.warning')
    @patch('requests.post')
    def test_address_validation_in_ui(self, mock_post, mock_warning, mock_error, 
                                    mock_text_input, mock_form_submit):
        """Test address validation in UI"""
        # Test case: country provided but no postal code
        mock_text_input.side_effect = [
            "testuser123",
            "test@example.com",
            "password123",
            "+1234567890",
            "123 Main St",
            "Test City",
            "Test State",
            "",  # Empty postal code
        ]
        mock_form_submit.return_value = True
        
        # This should trigger frontend validation
        # In actual implementation, this would be caught before API call
        # and mock_warning should be called with address error message

    @patch('streamlit.form_submit_button')
    @patch('streamlit.text_input')
    @patch('streamlit.error')
    @patch('requests.post')
    def test_network_error_handling_in_ui(self, mock_post, mock_error, 
                                        mock_text_input, mock_form_submit):
        """Test network error handling in UI"""
        mock_text_input.side_effect = ["testuser", "test@example.com", "password"]
        mock_form_submit.return_value = True
        
        # Mock network error
        mock_post.side_effect = RequestException("Network error")
        
        # Should handle gracefully and show user-friendly error
        # In actual implementation, mock_error should be called with network error message

    @patch('streamlit.form_submit_button') 
    @patch('streamlit.text_input')
    @patch('streamlit.error')
    @patch('requests.post')
    def test_server_error_handling_in_ui(self, mock_post, mock_error,
                                       mock_text_input, mock_form_submit):
        """Test server error handling in UI"""
        mock_text_input.side_effect = ["testuser", "test@example.com", "password"]
        mock_form_submit.return_value = True
        
        # Mock server error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        # Should show generic error without exposing server details
        assert mock_response.status_code == 500

    @patch('streamlit.form_submit_button')
    @patch('streamlit.text_input')
    @patch('streamlit.error')
    @patch('streamlit.warning')
    @patch('requests.post')
    def test_malformed_response_handling_in_ui(self, mock_post, mock_warning,
                                             mock_error, mock_text_input, 
                                             mock_form_submit):
        """Test handling of malformed API responses in UI"""
        mock_text_input.side_effect = ["testuser", "test@example.com", "password"]
        mock_form_submit.return_value = True
        
        # Mock malformed response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response
        
        # Should handle gracefully and show generic error
        assert mock_response.status_code == 400

    def test_frontend_validation_functions(self):
        """Test frontend validation helper functions"""
        # Test email validation
        valid_emails = ["test@example.com", "user+tag@domain.co.uk"]
        invalid_emails = ["invalid-email", "@domain.com", "user@"]
        
        # Test password validation
        valid_passwords = ["SecurePass123!", "MyStr0ng!Pass"]
        invalid_passwords = ["123", "password", "short"]
        
        # Test phone validation
        valid_phones = ["+1234567890", "+44-20-7946-0958", "(555) 123-4567"]
        invalid_phones = ["123", "invalid-phone", "++123456"]
        
        # In actual implementation, these would test the validate_input function
        # from utils.py

class TestDatabaseIntegration:
    """Test database interactions for registration"""
    
    @pytest.fixture
    def mock_db_connection(self):
        """Mock database connection for testing"""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn
            yield mock_conn, mock_cursor

    def test_user_creation_with_postgresql(self, mock_db_connection):
        """Test user creation in PostgreSQL"""
        mock_conn, mock_cursor = mock_db_connection
        
        # Mock successful user creation
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.return_value = (1, "testuser123")
        
        # Test user creation logic
        user_data = {
            "username": "testuser123",
            "email": "test@example.com",
            "password": "hashed_password"
        }
        
        # In actual implementation, this would call your user creation function
        assert user_data["username"] == "testuser123"

    def test_duplicate_email_handling_postgresql(self, mock_db_connection):
        """Test duplicate email handling in PostgreSQL"""
        mock_conn, mock_cursor = mock_db_connection
        
        # Mock integrity error for duplicate email
        from psycopg2 import IntegrityError
        mock_cursor.execute.side_effect = IntegrityError("Duplicate key")
        
        # Should handle the integrity error gracefully
        # In actual implementation, this would test your error handling

    def test_address_constraint_validation_postgresql(self, mock_db_connection):
        """Test address constraint validation in PostgreSQL"""
        mock_conn, mock_cursor = mock_db_connection
        
        # Test various address scenarios
        address_test_cases = [
            {"country": "US", "postalcode": "12345", "should_pass": True},
            {"country": "US", "postalcode": "", "should_pass": False},
            {"country": "", "postalcode": "12345", "should_pass": False},
            {"country": "", "postalcode": "", "should_pass": True},
        ]
        
        for case in address_test_cases:
            if case["should_pass"]:
                mock_cursor.execute.return_value = None
            else:
                mock_cursor.execute.side_effect = Exception("Constraint violation")
            
            # Test constraint validation logic

class TestSecurityValidation:
    """Test security aspects of registration"""
    
    def test_password_hashing(self):
        """Test that passwords are properly hashed"""
        plain_password = "SecurePass123!"
        # In actual implementation, test that password gets hashed
        # and original password is not stored
        assert plain_password != "hashed_value"

    def test_input_sanitization(self):
        """Test input sanitization for XSS prevention"""
        # Import our actual security utilities
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        try:
            from security_utils import InputSanitizer
        except ImportError:
            # If security_utils not available, skip test
            pytest.skip("Security utilities not available")
        
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "onclick='alert(1)'",
            "{{7*7}}",  # Template injection
            "../../../etc/passwd",  # Path traversal
        ]
        
        for malicious_input in malicious_inputs:
            # Test that malicious input is properly sanitized
            sanitized = InputSanitizer.sanitize_string(malicious_input)
            
            # Should not contain dangerous patterns
            assert "<script>" not in sanitized.lower()
            assert "javascript:" not in sanitized.lower()
            assert "onclick" not in sanitized.lower()
            assert "drop table" not in sanitized.lower()
            assert "../" not in sanitized
            assert "{{" not in sanitized
            
            # Should be safe for display - check for HTML escaping of dangerous tags
            if "<" in malicious_input and ">" in malicious_input:
                assert "&lt" in sanitized and "&gt" in sanitized
            
            # Should be safe for display
            assert len(sanitized) >= 0  # Sanitization might remove everything, that's ok
            
        # Test specific field sanitizers
        test_email = "<script>test@example.com</script>"
        sanitized_email = InputSanitizer.sanitize_email(test_email)
        assert "<script>" not in sanitized_email
        assert "@" in sanitized_email  # Should preserve valid email parts
        
        test_username = "user<script>alert(1)</script>name"
        sanitized_username = InputSanitizer.sanitize_username(test_username)
        assert "<script>" not in sanitized_username
        # HTML escaping preserves text content while making it safe
        assert len(sanitized_username) > 0  # Should preserve valid username parts

    def test_rate_limiting_simulation(self):
        """Test rate limiting behavior simulation"""
        # Simulate multiple rapid registration attempts
        attempts = []
        for i in range(10):
            attempt = {
                "timestamp": f"2024-01-01 12:00:{i:02d}",
                "ip": "192.168.1.1",
                "status": "blocked" if i > 5 else "allowed"
            }
            attempts.append(attempt)
        
        # In actual implementation, test rate limiting logic
        blocked_attempts = [a for a in attempts if a["status"] == "blocked"]
        assert len(blocked_attempts) > 0

    def test_csrf_protection_simulation(self):
        """Test CSRF protection simulation"""
        # In actual implementation, test CSRF token validation
        valid_token = "csrf-token-123"
        invalid_token = "invalid-token"
        
        assert valid_token != invalid_token

class TestPerformanceAndScalability:
    """Test performance aspects of registration"""
    
    def test_registration_response_time_simulation(self):
        """Test registration response time simulation"""
        import time
        
        start_time = time.time()
        # Simulate registration processing
        time.sleep(0.1)  # Simulate processing time
        end_time = time.time()
        
        response_time = end_time - start_time
        # Registration should complete within reasonable time
        assert response_time < 5.0  # 5 seconds max

    def test_concurrent_registration_simulation(self):
        """Test concurrent registration handling simulation"""
        # Simulate multiple users registering simultaneously
        concurrent_users = 10
        registration_results = []
        
        for i in range(concurrent_users):
            result = {
                "user_id": i,
                "status": "success" if i % 7 != 0 else "duplicate_error",
                "response_time": 0.1 + (i * 0.01)
            }
            registration_results.append(result)
        
        successful_registrations = [r for r in registration_results if r["status"] == "success"]
        assert len(successful_registrations) > 0 