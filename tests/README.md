# Registration Testing Suite

This directory contains comprehensive tests for the registration functionality, focusing on validation, security, and error handling.

## 🎯 Test Coverage

### Security Tests
- ✅ Email enumeration prevention
- ✅ SQL injection protection
- ✅ XSS attack prevention
- ✅ Input sanitization
- ✅ Error message security

### Validation Tests
- ✅ Address validation (country + postal code together)
- ✅ Email format validation
- ✅ Password strength validation
- ✅ Phone number validation
- ✅ Required field validation

### Integration Tests
- ✅ Complete registration flow
- ✅ Database integrity errors
- ✅ Network error handling
- ✅ Server error handling
- ✅ Malformed response handling

## 🚀 Running Tests

### 1. Automated Tests (CI/CD)

The GitHub Actions workflow automatically runs tests on every push:

```bash
# Tests run automatically on:
# - Push to main/develop branches
# - Pull requests to main
# - Manual workflow dispatch
```

### 2. Local Testing with pytest

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run specific test files
pytest tests/test_registration.py
pytest tests/test_integration.py

# Run with coverage
pytest --cov=views --cov-report=html

# Run with verbose output
pytest -v --tb=short
```

### 3. Manual Testing Script

For comprehensive manual testing of the registration API:

```bash
# Run the interactive test suite
python tests/manual_registration_test.py

# Choose from:
# 1. Run all tests automatically
# 2. Interactive testing mode
# 3. Address validation tests only
# 4. Security tests only
```

## 🐛 Test Categories

### Unit Tests (`test_registration.py`)
- Individual validation functions
- Error handling scenarios
- Security message filtering
- Response code validation

### Integration Tests (`test_integration.py`)
- Streamlit form integration
- Database interaction simulation
- End-to-end registration flow
- Performance testing

### Manual Tests (`manual_registration_test.py`)
- Real API endpoint testing
- Security scenario validation
- Address validation edge cases
- Interactive testing modes

## 🔒 Security Test Scenarios

### Email Enumeration Prevention
```python
# ❌ Bad: Reveals email exists
"An account with this email already exists"

# ✅ Good: Generic message
"Registration failed. Please check your information and try again."
```

### Username vs Email Handling
```python
# ✅ Username errors (acceptable)
"This username is already taken. Please choose a different one."

# ✅ Email errors (secure)
"Registration failed. Please check your information and try again."
```

### Address Validation
```python
# Test cases:
✅ Both country and postal code provided
✅ Neither country nor postal code provided
❌ Country provided without postal code
❌ Postal code provided without country
```

## 🗄️ Database Testing

### PostgreSQL Integration
The CI/CD pipeline includes:
- PostgreSQL 15 service container
- Database connection testing
- Constraint validation testing
- Transaction rollback testing

### Test Database Setup
```yaml
# Automatically configured in CI/CD
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_DB: test_sautai
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_password
```

## 📊 Test Reports

### Automated Reports
- Test results uploaded as artifacts
- HTML reports generated for failed tests
- Coverage reports (when enabled)

### Manual Test Output
```
🧪 Testing: Valid Registration
Expected: Should successfully register user
Status: 200
✅ PASSED: Status code matches expectation

📊 TEST SUMMARY
Total Tests: 11
✅ Passed: 10
❌ Failed: 1
Success Rate: 90.9%
```

## 🔧 Configuration

### pytest.ini
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests
    integration: Integration tests
    security: Security-focused tests
    performance: Performance tests
```

### Environment Variables
```bash
# For testing
DATABASE_URL=postgresql://test_user:test_password@localhost:5432/test_sautai
DJANGO_URL=http://localhost:8000
SECRET_KEY=test-secret-key-for-ci-cd
DEBUG=False
```

## 🎯 Key Test Scenarios

### 1. Security Validation
```bash
# Run security-focused tests
pytest -m security tests/

# Test email enumeration prevention
python tests/manual_registration_test.py
# Choose option 2 (Email Enumeration)
```

### 2. Address Validation
```bash
# Test all address scenarios
pytest tests/test_registration.py::TestRegistrationValidation::test_address_validation_both_country_postal_required

# Manual address testing
python tests/manual_registration_test.py
# Choose option 3 (Address Validation)
```

### 3. Error Message Security
```bash
# Verify error messages don't leak information
pytest tests/test_registration.py::TestRegistrationValidation::test_error_message_security
```

## 🚨 Important Notes

1. **Email Enumeration**: Tests verify that email existence is never revealed
2. **Username Enumeration**: Username availability can be revealed (acceptable UX)
3. **Error Messages**: All error messages are sanitized to prevent information disclosure
4. **Database Constraints**: Tests handle PostgreSQL integrity errors gracefully
5. **Rate Limiting**: Consider implementing and testing rate limiting for production

## 📈 Adding New Tests

### For new validation rules:
1. Add test case to `test_registration.py`
2. Update manual test script with new scenario
3. Ensure error messages don't leak information
4. Test both frontend and backend validation

### For new security features:
1. Add to security test class
2. Document expected behavior
3. Test with malicious inputs
4. Verify proper sanitization

## 🔄 Continuous Integration

The CI/CD pipeline ensures:
- ✅ All tests pass before deployment
- ✅ PostgreSQL compatibility
- ✅ Security validations work correctly
- ✅ Error handling is robust
- ✅ Performance is acceptable

Tests must pass for deployment to proceed to production environment. 