# Testing and Evaluation

AquaSense was evaluated using functional, non-functional, usability, performance, and compatibility testing.

## Functional Testing Areas

- User registration
- Login and session management
- Token refresh mechanism
- Terms and conditions acceptance
- District and profile setup
- Network creation
- Zone configuration
- Two-Factor Authentication enablement and verification
- Zone analytics summary retrieval
- Detailed zone analytics retrieval
- User profile retrieval
- Frontend UI behaviour

## Non-Functional Testing Areas

- Performance
- Usability
- Reliability
- Compatibility
- Real-time responsiveness
- Security behaviour

## Usability Test Summary

| Task | Result |
|---|---|
| Locate current flow rate on dashboard | Successful |
| Navigate to Kitchen zone and toggle valve | Mostly successful |
| Generate monthly report | Successful |
| Find registered plumber by district | Successful |

## Performance Notes

- Leak detection target: near real-time alert and valve response
- Backend uses batch writes to reduce database load
- Daily summaries improve chart and analytics performance
- Render free-tier cold starts may delay the first request in production

## Compatibility Notes

Test across:

- Android
- iOS-style Flutter layout
- Web deployment
- Different screen sizes
- Different network states

## Manual Production Smoke Test

1. Visit frontend URL.
2. Check backend `/health`.
3. Register/login.
4. Load profile.
5. Open dashboard.
6. Trigger or simulate device data.
7. Verify analytics page loads.
8. Check Render logs for errors.
9. Confirm Firebase app calls Render API URL.
