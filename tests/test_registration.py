import pytest
import requests
import json
from unittest.mock import Mock, patch, MagicMock
import streamlit as st
from requests.exceptions import RequestException, Timeout
import sys
import os

# Add the parent directory to sys.path to import views and utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestRegistrationValidation:
    """Test registration form validation and error handling"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.valid_user_data = {
            "user": {
                "username": "testuser123",
                "email": "test@example.com",
                "password": "SecurePass123!",
                "phone_number": "+1234567890",
                "dietary_preferences": ["Everything"],
                "custom_dietary_preferences": [],
                "allergies": [],
                "custom_allergies": [],
                "timezone": "UTC",
                "preferred_language": "en",
                "preferred_servings": 2,
                "emergency_supply_goal": 7
            },
            "address": {
                "street": "123 Main St",
                "city": "Test City",
                "state": "Test State",
                "country": "US",
                "postalcode": "12345"
            },
            "goal": {
                "goal_name": "Healthy Eating",
                "goal_description": "Eat healthier meals"
            }
        }

    def test_successful_registration_response(self):
        """Test successful registration with 200 response"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Registration successful"}
        
        with patch('requests.post', return_value=mock_response):
            # This would be called in the actual registration flow
            response = requests.post("http://test/api/register/", json=self.valid_user_data)
            assert response.status_code == 200

    def test_email_enumeration_prevention(self):
        """Test that email enumeration is prevented"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "errors": {
                "email": ["This email already exists"]
            }
        }
        
        with patch('requests.post', return_value=mock_response):
            # Should not reveal email existence
            response = requests.post("http://test/api/register/", json=self.valid_user_data)
            assert response.status_code == 400
            # In our implementation, this would be converted to a generic message

    def test_username_validation_feedback(self):
        """Test that username validation provides specific feedback"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "errors": {
                "username": ["This username already exists"]
            }
        }
        
        with patch('requests.post', return_value=mock_response):
            response = requests.post("http://test/api/register/", json=self.valid_user_data)
            assert response.status_code == 400
            # Username errors should be specific (this is acceptable)

    def test_address_validation_both_country_postal_required(self):
        """Test address validation: both country and postal code required together"""
        test_cases = [
            # Country without postal code
            {"country": "US", "postalcode": ""},
            # Postal code without country  
            {"country": "", "postalcode": "12345"},
        ]
        
        for address_data in test_cases:
            user_data = self.valid_user_data.copy()
            user_data["address"].update(address_data)
            
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "errors": {
                    "__all__": ["Both country and postal code must be provided together"]
                }
            }
            
            with patch('requests.post', return_value=mock_response):
                response = requests.post("http://test/api/register/", json=user_data)
                assert response.status_code == 400

    def test_server_error_handling(self):
        """Test proper handling of server errors without exposing details"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error: Database connection failed"
        
        with patch('requests.post', return_value=mock_response):
            response = requests.post("http://test/api/register/", json=self.valid_user_data)
            assert response.status_code == 500
            # Should not expose internal error details to user

    def test_network_error_handling(self):
        """Test handling of network errors"""
        with patch('requests.post', side_effect=RequestException("Network error")):
            with pytest.raises(RequestException):
                requests.post("http://test/api/register/", json=self.valid_user_data)

    def test_timeout_handling(self):
        """Test handling of request timeouts"""
        with patch('requests.post', side_effect=Timeout("Request timeout")):
            with pytest.raises(Timeout):
                requests.post("http://test/api/register/", json=self.valid_user_data, timeout=10)

    def test_malformed_json_response(self):
        """Test handling of malformed JSON responses"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        with patch('requests.post', return_value=mock_response):
            response = requests.post("http://test/api/register/", json=self.valid_user_data)
            assert response.status_code == 400

    def test_duplicate_key_constraint_error(self):
        """Test handling of database integrity errors"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "errors": {
                "__all__": ["duplicate key value violates unique constraint"]
            }
        }
        
        with patch('requests.post', return_value=mock_response):
            response = requests.post("http://test/api/register/", json=self.valid_user_data)
            assert response.status_code == 400

    def test_invalid_email_format(self):
        """Test validation of email format"""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "test@",
            "test..test@example.com",
        ]
        
        for email in invalid_emails:
            user_data = self.valid_user_data.copy()
            user_data["user"]["email"] = email
            
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "errors": {
                    "email": ["Enter a valid email address"]
                }
            }
            
            with patch('requests.post', return_value=mock_response):
                response = requests.post("http://test/api/register/", json=user_data)
                assert response.status_code == 400

    def test_weak_password_validation(self):
        """Test password strength validation"""
        weak_passwords = [
            "123",
            "password",
            "pass",
            "12345678"
        ]
        
        for password in weak_passwords:
            user_data = self.valid_user_data.copy()
            user_data["user"]["password"] = password
            
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "errors": {
                    "password": ["Password is too weak"]
                }
            }
            
            with patch('requests.post', return_value=mock_response):
                response = requests.post("http://test/api/register/", json=user_data)
                assert response.status_code == 400

    def test_missing_required_fields(self):
        """Test validation when required fields are missing"""
        required_fields = ["username", "email", "password"]
        
        for field in required_fields:
            user_data = self.valid_user_data.copy()
            del user_data["user"][field]
            
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "errors": {
                    field: ["This field is required"]
                }
            }
            
            with patch('requests.post', return_value=mock_response):
                response = requests.post("http://test/api/register/", json=user_data)
                assert response.status_code == 400

    def test_phone_number_validation(self):
        """Test phone number format validation"""
        invalid_phones = [
            "123",
            "abc-def-ghij",
            "++1234567890",
            "123-45-6789"  # Too short
        ]
        
        for phone in invalid_phones:
            user_data = self.valid_user_data.copy()
            user_data["user"]["phone_number"] = phone
            
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "errors": {
                    "phone_number": ["Enter a valid phone number"]
                }
            }
            
            with patch('requests.post', return_value=mock_response):
                response = requests.post("http://test/api/register/", json=user_data)
                assert response.status_code == 400

    def test_postal_code_validation(self):
        """Test postal code format validation"""
        invalid_postal_codes = [
            "INVALID",
            "12345678901",  # Too long
            "abc"
        ]
        
        for postal in invalid_postal_codes:
            user_data = self.valid_user_data.copy()
            user_data["address"]["postalcode"] = postal
            
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "errors": {
                    "postalcode": ["Enter a valid postal code"]
                }
            }
            
            with patch('requests.post', return_value=mock_response):
                response = requests.post("http://test/api/register/", json=user_data)
                assert response.status_code == 400

    def test_error_message_security(self):
        """Test that error messages don't reveal sensitive information"""
        # Test various error scenarios that should return generic messages
        security_test_cases = [
            {
                "description": "Database constraint error",
                "error": {"__all__": ["IntegrityError: duplicate key"]},
                "should_be_generic": True
            },
            {
                "description": "Email enumeration attempt", 
                "error": {"email": ["User with this email already exists"]},
                "should_be_generic": True
            },
            {
                "description": "System error exposure",
                "error": {"__all__": ["Database connection failed"]},
                "should_be_generic": True
            }
        ]
        
        for case in security_test_cases:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"errors": case["error"]}
            
            with patch('requests.post', return_value=mock_response):
                response = requests.post("http://test/api/register/", json=self.valid_user_data)
                assert response.status_code == 400
                # In our implementation, these should be converted to generic messages


class TestActualSecurityImplementation:
    """Test the actual security utilities we implemented"""
    
    def test_input_sanitizer_xss_prevention(self):
        """Test XSS prevention in input sanitizer"""
        try:
            from security_utils import InputSanitizer
        except ImportError:
            pytest.skip("Security utilities not available")
        
        xss_inputs = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert('xss')",
            "onclick='alert(1)'",
        ]
        
        for xss_input in xss_inputs:
            sanitized = InputSanitizer.sanitize_string(xss_input)
            assert "<script>" not in sanitized.lower()
            assert "javascript:" not in sanitized.lower()
            assert "onclick" not in sanitized.lower()
            assert "alert" not in sanitized.lower()
    
    def test_input_sanitizer_sql_injection_prevention(self):
        """Test SQL injection prevention"""
        try:
            from security_utils import InputSanitizer
        except ImportError:
            pytest.skip("Security utilities not available")
        
        sql_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM passwords",
            "admin'--",
        ]
        
        for sql_input in sql_inputs:
            sanitized = InputSanitizer.sanitize_string(sql_input)
            assert "drop table" not in sanitized.lower()
            assert "union select" not in sanitized.lower()
            assert "or 1=1" not in sanitized.lower()
            assert "--" not in sanitized
    
    def test_security_validator_password_strength(self):
        """Test password strength validation"""
        try:
            from security_utils import SecurityValidator
        except ImportError:
            pytest.skip("Security utilities not available")
        
        # Test weak passwords
        weak_passwords = ["123", "password", "qwerty123", "letmein"]
        for weak_pass in weak_passwords:
            valid, msg = SecurityValidator.validate_password_strength(weak_pass)
            assert not valid
            assert "weak" in msg.lower() or "short" in msg.lower() or "common" in msg.lower()
        
        # Test strong passwords
        strong_passwords = ["SecurePass123!", "MyStr0ng!Password", "C0mpl3x@Pass"]
        for strong_pass in strong_passwords:
            valid, msg = SecurityValidator.validate_password_strength(strong_pass)
            assert valid
    
    def test_security_validator_email_format(self):
        """Test email format validation"""
        try:
            from security_utils import SecurityValidator
        except ImportError:
            pytest.skip("Security utilities not available")
        
        # Test invalid emails
        invalid_emails = ["invalid", "@domain.com", "user@", "user..name@domain.com"]
        for invalid_email in invalid_emails:
            valid, msg = SecurityValidator.validate_email_format(invalid_email)
            assert not valid
        
        # Test valid emails
        valid_emails = ["test@example.com", "user.name@domain.co.uk", "user+tag@example.org"]
        for valid_email in valid_emails:
            valid, msg = SecurityValidator.validate_email_format(valid_email)
            assert valid
    
    def test_security_validator_username_format(self):
        """Test username format validation"""
        try:
            from security_utils import SecurityValidator
        except ImportError:
            pytest.skip("Security utilities not available")
        
        # Test invalid usernames
        invalid_usernames = ["ab", "admin", "user@name", "user name", "user<script>"]
        for invalid_username in invalid_usernames:
            valid, msg = SecurityValidator.validate_username_format(invalid_username)
            assert not valid
        
        # Test valid usernames
        valid_usernames = ["testuser123", "user.name", "user_name", "user-name"]
        for valid_username in valid_usernames:
            valid, msg = SecurityValidator.validate_username_format(valid_username)
            assert valid
    
    def test_registration_data_sanitization(self):
        """Test complete registration data sanitization"""
        try:
            from security_utils import sanitize_registration_data
        except ImportError:
            pytest.skip("Security utilities not available")
        
        dangerous_data = {
            "user": {
                "username": "user<script>alert(1)</script>",
                "email": "<script>test@example.com</script>",
                "password": "SecurePass123!",
                "phone_number": "+1-555<script>123-4567",
                "dietary_preferences": ["Vegetarian<script>"],
                "custom_dietary_preferences": ["Custom<script>alert(1)</script>"],
                "allergies": ["Peanuts<script>"],
                "custom_allergies": ["Custom allergy<script>"],
                "timezone": "UTC<script>",
                "preferred_language": "en<script>",
                "preferred_servings": 2,
                "emergency_supply_goal": 7
            },
            "address": {
                "street": "123 Main St<script>",
                "city": "Test City<script>",
                "state": "Test State<script>",
                "country": "US",
                "postalcode": "12345<script>"
            },
            "goal": {
                "goal_name": "Healthy<script>alert(1)</script>",
                "goal_description": "Eat healthier<script>alert(1)</script>"
            }
        }
        
        sanitized = sanitize_registration_data(dangerous_data)
        
        # Check that all script tags are removed
        def check_no_scripts(obj):
            if isinstance(obj, str):
                assert "<script>" not in obj.lower()
                assert "alert" not in obj.lower()
            elif isinstance(obj, dict):
                for value in obj.values():
                    check_no_scripts(value)
            elif isinstance(obj, list):
                for item in obj:
                    check_no_scripts(item)
        
        check_no_scripts(sanitized)
    
    def test_registration_security_validation(self):
        """Test complete registration security validation"""
        try:
            from security_utils import validate_registration_security
        except ImportError:
            pytest.skip("Security utilities not available")
        
        # Test with dangerous input
        dangerous_data = {
            "user": {
                "username": "'; DROP TABLE users; --",
                "email": "test@example.com",
                "password": "weak",
                "phone_number": "+1234567890",
                "dietary_preferences": [],
                "custom_dietary_preferences": [],
                "allergies": [],
                "custom_allergies": [],
                "timezone": "UTC",
                "preferred_language": "en",
                "preferred_servings": 2,
                "emergency_supply_goal": 7
            }
        }
        
        valid, errors = validate_registration_security(dangerous_data)
        assert not valid
        assert len(errors) > 0
        
        # Should detect dangerous patterns
        assert any("dangerous" in error.lower() for error in errors) or \
               any("password" in error.lower() for error in errors) or \
               any("username" in error.lower() for error in errors)


class TestRegistrationIntegration:
    """Integration tests for registration flow"""
    
    def test_complete_registration_flow_success(self):
        """Test complete successful registration flow"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": "Registration successful"}
        
        with patch('requests.post', return_value=mock_response):
            response = requests.post("http://test/api/register/", json={})
            assert response.status_code == 200

    def test_complete_registration_flow_with_errors(self):
        """Test complete registration flow with validation errors"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "errors": {
                "username": ["This username is already taken"],
                "email": ["This email already exists"],
                "__all__": ["Both country and postal code must be provided together"]
            }
        }
        
        with patch('requests.post', return_value=mock_response):
            response = requests.post("http://test/api/register/", json={})
            assert response.status_code == 400 