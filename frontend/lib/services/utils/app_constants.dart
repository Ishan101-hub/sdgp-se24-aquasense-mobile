class AppConstants {
  // ─────────────────────────────────────────────
  // BASE URL
  // Using 127.0.0.1 for Chrome browser testing
  // Change back to http://10.0.2.2:8000 when testing on Android emulator
  // ─────────────────────────────────────────────
  static const String baseUrl = "http://127.0.0.1:8000";

  // ─────────────────────────────────────────────
  // AUTH ENDPOINTS
  // ─────────────────────────────────────────────
  static const String register = "/auth/register";
  static const String verifyOtp = "/auth/verify-otp";
  static const String login = "/auth/login";
  static const String logout = "/auth/logout";
  static const String forgotPassword = "/auth/forgot-password";
  static const String resetPassword = "/auth/reset-password";
  static const String changePassword = "/auth/change-password";
  static const String resendOtp = "/auth/resend-otp";
  static const String refreshToken = "/auth/refresh-token";
  static const String verify2FALogin = "/auth/2fa/verify-login";

  // ─────────────────────────────────────────────
  // USER ENDPOINTS
  // ─────────────────────────────────────────────
  static const String profile = "/user/profile";
  static const String updateProfile = "/user/update-profile";
  static const String deleteAccount = "/user/delete-account";
  static const String registerDevice = "/user/register-device";
 
  // ─────────────────────────────────────────────
  // TERMS ENDPOINTS
  // ─────────────────────────────────────────────
  static const String termsCheck = "/terms/check";
  static const String termsStatus = "/terms/status";
  static const String termsSave = "/terms/save";

  // ─────────────────────────────────────────────
  // DISTRICT ENDPOINTS
  // ─────────────────────────────────────────────
  static const String allDistricts = "/district/all";
  static const String myDistrict = "/district/my-district";
  static const String saveDistrict = "/district/save";

  // ─────────────────────────────────────────────
  // SECURITY ENDPOINTS
  // ─────────────────────────────────────────────
  static const String securitySettings = "/security/settings";
  static const String enable2FA = "/security/2fa/enable";
  static const String verifyEnable2FA = "/security/2fa/verify-enable";
  static const String disable2FA = "/security/2fa/disable";
  static const String loginAlerts = "/security/login-alerts";
  static const String autoLock = "/security/auto-lock";
}