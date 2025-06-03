#!/usr/bin/env python3
"""
Manual Registration Testing Script

This script helps you manually test all registration scenarios to ensure
validation works correctly and error messages are displayed properly.

Usage: python tests/manual_registration_test.py
"""

import requests
import json
import time
from typing import Dict, Any, List, Tuple

class RegistrationTester:
    """Manual testing helper for registration functionality"""
    
    def __init__(self, api_url: str = "http://localhost:8000/auth/api/register/"):
        self.api_url = api_url
        self.test_results: List[Dict[str, Any]] = []
    
    def test_case(self, name: str, user_data: Dict[str, Any], expected_status: int, 
                  expected_behavior: str) -> bool:
        """Run a single test case and record results"""
        print(f"\n🧪 Testing: {name}")
        print(f"Expected: {expected_behavior}")
        
        try:
            response = requests.post(self.api_url, json=user_data, timeout=10)
            
            result = {
                "name": name,
                "status_code": response.status_code,
                "expected_status": expected_status,
                "passed": response.status_code == expected_status,
                "response_data": None,
                "error": None
            }
            
            try:
                result["response_data"] = response.json()
            except:
                result["response_data"] = response.text
            
            print(f"Status: {response.status_code}")
            if response.status_code != expected_status:
                print(f"❌ FAILED: Expected {expected_status}, got {response.status_code}")
                result["passed"] = False
            else:
                print(f"✅ PASSED: Status code matches expectation")
            
            if hasattr(response, 'json') and response.status_code == 400:
                try:
                    error_data = response.json()
                    print(f"Response data: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"Response text: {response.text}")
            
            self.test_results.append(result)
            return result["passed"]
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            result = {
                "name": name,
                "status_code": None,
                "expected_status": expected_status,
                "passed": False,
                "response_data": None,
                "error": str(e)
            }
            self.test_results.append(result)
            return False
    
    def run_all_tests(self):
        """Run comprehensive registration tests"""
        print("🚀 Starting Comprehensive Registration Testing")
        print("=" * 60)
        
        # Test 1: Valid Registration
        valid_user = {
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
        
        self.test_case(
            "Valid Registration",
            valid_user,
            200,
            "Should successfully register user"
        )
        
        # Test 2: Duplicate Email (should not reveal existence)
        duplicate_email_user = valid_user.copy()
        duplicate_email_user["user"]["email"] = "existing@example.com"
        duplicate_email_user["user"]["username"] = "differentuser"
        
        self.test_case(
            "Duplicate Email Test",
            duplicate_email_user,
            400,
            "Should show generic error without revealing email exists"
        )
        
        # Test 3: Duplicate Username (can show specific error)
        duplicate_username_user = valid_user.copy()
        duplicate_username_user["user"]["username"] = "existinguser"
        duplicate_username_user["user"]["email"] = "different@example.com"
        
        self.test_case(
            "Duplicate Username Test",
            duplicate_username_user,
            400,
            "Should show specific username error"
        )
        
        # Test 4: Missing Country/Postal Code Validation
        missing_postal_user = valid_user.copy()
        missing_postal_user["address"]["postalcode"] = ""
        
        self.test_case(
            "Missing Postal Code",
            missing_postal_user,
            400,
            "Should require both country and postal code together"
        )
        
        # Test 5: Missing Country with Postal Code
        missing_country_user = valid_user.copy()
        missing_country_user["address"]["country"] = ""
        
        self.test_case(
            "Missing Country",
            missing_country_user,
            400,
            "Should require both country and postal code together"
        )
        
        # Test 6: Invalid Email Format
        invalid_email_user = valid_user.copy()
        invalid_email_user["user"]["email"] = "invalid-email"
        invalid_email_user["user"]["username"] = "uniqueuser1"
        
        self.test_case(
            "Invalid Email Format",
            invalid_email_user,
            400,
            "Should reject invalid email format"
        )
        
        # Test 7: Weak Password
        weak_password_user = valid_user.copy()
        weak_password_user["user"]["password"] = "123"
        weak_password_user["user"]["username"] = "uniqueuser2"
        weak_password_user["user"]["email"] = "unique2@example.com"
        
        self.test_case(
            "Weak Password",
            weak_password_user,
            400,
            "Should reject weak password"
        )
        
        # Test 8: Missing Required Fields
        missing_username_user = valid_user.copy()
        del missing_username_user["user"]["username"]
        
        self.test_case(
            "Missing Username",
            missing_username_user,
            400,
            "Should require username field"
        )
        
        # Test 9: Invalid Phone Number
        invalid_phone_user = valid_user.copy()
        invalid_phone_user["user"]["phone_number"] = "invalid-phone"
        invalid_phone_user["user"]["username"] = "uniqueuser3"
        invalid_phone_user["user"]["email"] = "unique3@example.com"
        
        self.test_case(
            "Invalid Phone Number",
            invalid_phone_user,
            400,
            "Should reject invalid phone format"
        )
        
        # Test 10: SQL Injection Attempt
        sql_injection_user = valid_user.copy()
        sql_injection_user["user"]["username"] = "'; DROP TABLE users; --"
        sql_injection_user["user"]["email"] = "injection@example.com"
        
        self.test_case(
            "SQL Injection Attempt",
            sql_injection_user,
            400,
            "Should safely handle SQL injection attempt"
        )
        
        # Test 11: XSS Attempt
        xss_user = valid_user.copy()
        xss_user["user"]["username"] = "<script>alert('xss')</script>"
        xss_user["user"]["email"] = "xss@example.com"
        
        self.test_case(
            "XSS Attempt",
            xss_user,
            400,
            "Should safely handle XSS attempt"
        )
        
        print("\n" + "=" * 60)
        self.print_summary()
    
    def test_security_scenarios(self):
        """Test specific security scenarios"""
        print("\n🔒 Security Testing Scenarios")
        print("=" * 40)
        
        # Test email enumeration prevention
        print("\n📧 Email Enumeration Test:")
        print("Try registering with the same email multiple times.")
        print("Observe that the error message doesn't reveal if email exists.")
        
        # Test rate limiting (if implemented)
        print("\n⏱️ Rate Limiting Test:")
        print("Try multiple rapid registrations from same IP.")
        print("Should be rate limited after several attempts.")
        
        # Test input sanitization
        print("\n🧹 Input Sanitization Test:")
        print("Try various malicious inputs in all fields.")
        print("Should be properly sanitized without causing errors.")
    
    def test_address_validation_scenarios(self):
        """Test address validation edge cases"""
        print("\n🏠 Address Validation Testing")
        print("=" * 40)
        
        base_user = {
            "user": {
                "username": "addresstest",
                "email": "address@example.com", 
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
                "street": "",
                "city": "",
                "state": "",
                "country": "",
                "postalcode": ""
            },
            "goal": {
                "goal_name": "Test",
                "goal_description": "Test"
            }
        }
        
        # Test various address combinations
        address_scenarios = [
            {
                "name": "Complete Address",
                "address": {"street": "123 Main St", "city": "Test City", "state": "Test State", "country": "US", "postalcode": "12345"},
                "expected": 200
            },
            {
                "name": "Empty Address",
                "address": {"street": "", "city": "", "state": "", "country": "", "postalcode": ""},
                "expected": 200
            },
            {
                "name": "Country Only",
                "address": {"street": "", "city": "", "state": "", "country": "US", "postalcode": ""},
                "expected": 400
            },
            {
                "name": "Postal Code Only",
                "address": {"street": "", "city": "", "state": "", "country": "", "postalcode": "12345"},
                "expected": 400
            }
        ]
        
        for i, scenario in enumerate(address_scenarios):
            test_user = base_user.copy()
            test_user["user"]["username"] = f"addresstest{i}"
            test_user["user"]["email"] = f"address{i}@example.com"
            test_user["address"] = scenario["address"]
            
            self.test_case(
                scenario["name"],
                test_user,
                scenario["expected"],
                f"Address validation for: {scenario['name']}"
            )
    
    def print_summary(self):
        """Print test results summary"""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["passed"])
        failed_tests = total_tests - passed_tests
        
        print(f"\n📊 TEST SUMMARY")
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  • {result['name']}: Expected {result['expected_status']}, got {result['status_code']}")
                    if result["error"]:
                        print(f"    Error: {result['error']}")
    
    def interactive_test(self):
        """Interactive testing mode"""
        print("\n🎮 Interactive Testing Mode")
        print("Test specific scenarios manually")
        
        while True:
            print("\nAvailable Tests:")
            print("1. Valid Registration")
            print("2. Email Enumeration")
            print("3. Address Validation")
            print("4. Security Tests")
            print("5. All Tests")
            print("6. Exit")
            
            choice = input("\nSelect test (1-6): ").strip()
            
            if choice == "1":
                print("Testing valid registration...")
                # Add specific test logic
            elif choice == "2":
                print("Testing email enumeration prevention...")
                # Add specific test logic
            elif choice == "3":
                self.test_address_validation_scenarios()
            elif choice == "4":
                self.test_security_scenarios()
            elif choice == "5":
                self.run_all_tests()
            elif choice == "6":
                break
            else:
                print("Invalid choice. Please select 1-6.")

def main():
    """Main function to run registration tests"""
    print("🧪 Registration Testing Suite")
    print("=" * 50)
    
    # Get API URL from user
    api_url = input("Enter Django API URL (default: http://localhost:8000/auth/api/register/): ").strip()
    if not api_url:
        api_url = "http://localhost:8000/auth/api/register/"
    
    tester = RegistrationTester(api_url)
    
    print("\nChoose testing mode:")
    print("1. Run all tests automatically")
    print("2. Interactive testing")
    print("3. Address validation tests only")
    print("4. Security tests only")
    
    choice = input("Select mode (1-4): ").strip()
    
    if choice == "1":
        tester.run_all_tests()
    elif choice == "2":
        tester.interactive_test()
    elif choice == "3":
        tester.test_address_validation_scenarios()
    elif choice == "4":
        tester.test_security_scenarios()
    else:
        print("Invalid choice. Running all tests...")
        tester.run_all_tests()

if __name__ == "__main__":
    main() 