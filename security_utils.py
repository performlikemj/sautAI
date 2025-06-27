"""
Security utilities for input sanitization and validation
"""

import re
import html
import bleach
from typing import Dict, Any, Optional, List, Tuple
import secrets
import hashlib
import time
from collections import defaultdict, deque
import logging

# Configure logging for security events
security_logger = logging.getLogger('security')

class InputSanitizer:
    """
    Comprehensive input sanitization for preventing XSS, SQL injection, and other attacks
    """
    
    # Allowed HTML tags (none for form inputs)
    ALLOWED_TAGS = []
    ALLOWED_ATTRIBUTES = {}
    
    # Dangerous patterns to detect and remove
    DANGEROUS_PATTERNS = [
        # JavaScript patterns
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        
        # SQL injection patterns
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|DECLARE)\b)',
        r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',
        r'(--|#|/\*|\*/)',
        
        # Command injection patterns
        r'(\b(eval|exec|system|shell_exec|passthru|file_get_contents)\b)',
        r'(\||&&|;|\$\(|\`)',
        
        # Path traversal patterns
        r'(\.\./|\.\.\\)',
        r'(/etc/passwd|/proc/|/dev/)',
        
        # Template injection patterns
        r'(\{\{|\}\}|\{%|\%\})',
    ]
    
    @classmethod
    def sanitize_string(cls, input_str: str, max_length: int = 1000) -> str:
        """
        Sanitize a string input for safe storage and display
        """
        if not isinstance(input_str, str):
            return ""
        
        # Truncate to max length
        sanitized = input_str[:max_length]
        
        # HTML escape to prevent XSS
        sanitized = html.escape(sanitized)
        
        # Use bleach for additional cleaning
        sanitized = bleach.clean(
            sanitized, 
            tags=cls.ALLOWED_TAGS, 
            attributes=cls.ALLOWED_ATTRIBUTES,
            strip=True
        )
        
        # Remove dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        # Normalize whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        
        return sanitized
    
    @classmethod
    def sanitize_email(cls, email: str) -> str:
        """
        Sanitize email input with additional email-specific validation
        """
        if not isinstance(email, str):
            return ""
        
        # Basic sanitization
        email = cls.sanitize_string(email, max_length=254)  # RFC 5321 limit
        
        # Remove any remaining dangerous characters for email
        email = re.sub(r'[<>"\'\`]', '', email)
        
        # Convert to lowercase for consistency
        email = email.lower().strip()
        
        return email
    
    @classmethod
    def sanitize_username(cls, username: str) -> str:
        """
        Sanitize username with alphanumeric and safe character restrictions
        """
        if not isinstance(username, str):
            return ""
        
        # Basic sanitization
        username = cls.sanitize_string(username, max_length=150)
        
        # Only allow alphanumeric, underscore, hyphen, and dot
        username = re.sub(r'[^a-zA-Z0-9_.-]', '', username)
        
        # Remove consecutive dots or special chars
        username = re.sub(r'[._-]{2,}', lambda m: m.group(0)[0], username)
        
        # Trim special characters from start/end
        username = username.strip('._-')
        
        return username
    
    @classmethod
    def sanitize_phone(cls, phone: str) -> str:
        """
        Sanitize phone number input
        """
        if not isinstance(phone, str):
            return ""
        
        # Basic sanitization
        phone = cls.sanitize_string(phone, max_length=20)
        
        # Only allow digits, +, -, (), and spaces
        phone = re.sub(r'[^0-9+\-() ]', '', phone)
        
        return phone.strip()
    
    @classmethod
    def sanitize_address_field(cls, field: str) -> str:
        """
        Sanitize address field (street, city, state)
        """
        if not isinstance(field, str):
            return ""
        
        # Basic sanitization
        field = cls.sanitize_string(field, max_length=255)
        
        # Remove special characters that could be dangerous
        field = re.sub(r'[<>{}[\]`]', '', field)
        
        return field.strip()


class SecurityValidator:
    """
    Security validation for registration inputs
    """
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """
        Validate password strength with comprehensive rules
        """
        if not password:
            return False, "Password is required"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if len(password) > 128:
            return False, "Password must not exceed 128 characters"
        
        # Check for common patterns
        if password.lower() in ['password', '12345678', 'qwerty123', 'letmein']:
            return False, "Password is too common"
        
        # Strength requirements
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'[0-9]', password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        
        score = sum([has_upper, has_lower, has_digit, has_special])
        
        if score < 3:
            return False, "Password must contain at least 3 of: uppercase, lowercase, numbers, special characters"
        
        return True, "Password is strong"
    
    @staticmethod
    def validate_email_format(email: str) -> Tuple[bool, str]:
        """
        Validate email format with security considerations
        """
        if not email:
            return False, "Email is required"
        
        # Basic format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, "Please enter a valid email address"
        
        # Check for suspicious patterns
        if '..' in email or email.startswith('.') or email.endswith('.'):
            return False, "Invalid email format"
        
        # Length validation
        if len(email) > 254:
            return False, "Email address is too long"
        
        return True, "Email is valid"
    
    @staticmethod
    def validate_username_format(username: str) -> Tuple[bool, str]:
        """
        Validate username format and security
        """
        if not username:
            return False, "Username is required"
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        if len(username) > 150:
            return False, "Username must not exceed 150 characters"
        
        # Only allow safe characters
        if not re.match(r'^[a-zA-Z0-9._-]+$', username):
            return False, "Username can only contain letters, numbers, dots, underscores, and hyphens"
        
        # Check for reserved usernames
        reserved_usernames = ['admin', 'root', 'system', 'api', 'www', 'mail', 'test']
        if username.lower() in reserved_usernames:
            return False, "This username is reserved"
        
        return True, "Username is valid"


class RateLimiter:
    """
    Simple in-memory rate limiter for registration attempts
    """
    
    def __init__(self, max_attempts: int = 5, window_minutes: int = 15):
        self.max_attempts = max_attempts
        self.window_seconds = window_minutes * 60
        self.attempts = defaultdict(deque)
    
    def is_rate_limited(self, identifier: str) -> bool:
        """
        Check if identifier (IP, email, etc.) is rate limited
        """
        now = time.time()
        attempts = self.attempts[identifier]
        
        # Remove old attempts outside the window
        while attempts and attempts[0] < now - self.window_seconds:
            attempts.popleft()
        
        # Check if exceeded limit
        if len(attempts) >= self.max_attempts:
            security_logger.warning(f"Rate limit exceeded for {identifier}")
            return True
        
        # Record this attempt
        attempts.append(now)
        return False


class CSRFProtection:
    """
    CSRF token generation and validation
    """
    
    @staticmethod
    def generate_csrf_token() -> str:
        """
        Generate a secure CSRF token
        """
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_csrf_token(token: str, session_token: str) -> bool:
        """
        Validate CSRF token against session token
        """
        if not token or not session_token:
            return False
        
        return secrets.compare_digest(token, session_token)


def sanitize_registration_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Comprehensive sanitization of registration data
    """
    sanitized = {}
    
    if 'user' in user_data:
        user = user_data['user']
        sanitized['user'] = {
            'username': InputSanitizer.sanitize_username(user.get('username', '')),
            'email': InputSanitizer.sanitize_email(user.get('email', '')),
            'password': user.get('password', ''),  # Don't sanitize password, just validate
            'phone_number': InputSanitizer.sanitize_phone(user.get('phone_number', '')),
            'dietary_preferences': [
                InputSanitizer.sanitize_string(pref, 50) 
                for pref in user.get('dietary_preferences', [])
                if isinstance(pref, str)
            ],
            'custom_dietary_preferences': [
                InputSanitizer.sanitize_string(pref, 100) 
                for pref in user.get('custom_dietary_preferences', [])
                if isinstance(pref, str)
            ],
            'allergies': [
                InputSanitizer.sanitize_string(allergy, 50) 
                for allergy in user.get('allergies', [])
                if isinstance(allergy, str)
            ],
            'custom_allergies': [
                InputSanitizer.sanitize_string(allergy, 100) 
                for allergy in user.get('custom_allergies', [])
                if isinstance(allergy, str)
            ],
            'timezone': InputSanitizer.sanitize_string(user.get('timezone', ''), 50),
            'preferred_language': InputSanitizer.sanitize_string(user.get('preferred_language', ''), 10),
            'household_member_count': int(user.get('household_member_count', 1)) if str(user.get('household_member_count', 1)).isdigit() else 1,
            'household_members': [
                {
                    'name': InputSanitizer.sanitize_string(member.get('name', ''), 100),
                    'age': int(member.get('age', 0)) if str(member.get('age', 0)).isdigit() else None,
                    'dietary_preferences': [
                        InputSanitizer.sanitize_string(pref, 50)
                        for pref in member.get('dietary_preferences', [])
                        if isinstance(pref, str)
                    ],
                    'notes': InputSanitizer.sanitize_string(member.get('notes', ''), 200)
                }
                for member in user.get('household_members', []) if isinstance(member, dict)
            ],
            'emergency_supply_goal': int(user.get('emergency_supply_goal', 0)) if str(user.get('emergency_supply_goal', 0)).isdigit() else 0
        }
    
    if 'address' in user_data:
        address = user_data['address']
        sanitized['address'] = {
            'street': InputSanitizer.sanitize_address_field(address.get('street', '')),
            'city': InputSanitizer.sanitize_address_field(address.get('city', '')),
            'state': InputSanitizer.sanitize_address_field(address.get('state', '')),
            'country': InputSanitizer.sanitize_string(address.get('country', ''), 5),
            'postalcode': InputSanitizer.sanitize_string(address.get('postalcode', ''), 20)
        }
    
    if 'goal' in user_data:
        goal = user_data['goal']
        sanitized['goal'] = {
            'goal_name': InputSanitizer.sanitize_string(goal.get('goal_name', ''), 100),
            'goal_description': InputSanitizer.sanitize_string(goal.get('goal_description', ''), 500)
        }
    
    return sanitized


def validate_registration_security(user_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Comprehensive security validation of registration data
    """
    errors = []
    
    if 'user' not in user_data:
        return False, ["Invalid user data structure"]
    
    user = user_data['user']
    
    # Validate username
    username_valid, username_msg = SecurityValidator.validate_username_format(user.get('username', ''))
    if not username_valid:
        errors.append(f"Username: {username_msg}")
    
    # Validate email
    email_valid, email_msg = SecurityValidator.validate_email_format(user.get('email', ''))
    if not email_valid:
        errors.append(f"Email: {email_msg}")
    
    # Validate password
    password_valid, password_msg = SecurityValidator.validate_password_strength(user.get('password', ''))
    if not password_valid:
        errors.append(f"Password: {password_msg}")
    
    # Check for suspicious input patterns
    all_text_fields = [
        user.get('username', ''),
        user.get('email', ''),
        str(user.get('phone_number', '')),
    ]
    
    # Add address fields if present
    if 'address' in user_data:
        address = user_data['address']
        all_text_fields.extend([
            address.get('street', ''),
            address.get('city', ''),
            address.get('state', ''),
            address.get('postalcode', '')
        ])
    
    # Add goal fields if present
    if 'goal' in user_data:
        goal = user_data['goal']
        all_text_fields.extend([
            goal.get('goal_name', ''),
            goal.get('goal_description', '')
        ])
    
    # Check for dangerous patterns in all fields
    for field_value in all_text_fields:
        if isinstance(field_value, str):
            for pattern in InputSanitizer.DANGEROUS_PATTERNS:
                if re.search(pattern, field_value, re.IGNORECASE):
                    errors.append("Input contains potentially dangerous content")
                    security_logger.warning(f"Dangerous pattern detected: {pattern[:20]}...")
                    break
    
    return len(errors) == 0, errors 