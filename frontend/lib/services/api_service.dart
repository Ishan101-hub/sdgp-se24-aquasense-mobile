import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/utils/app_constants.dart'; 

class ApiService {

  // ─────────────────────────────────────────────
  // HEADERS
  // ─────────────────────────────────────────────

  // Basic headers for public routes — register, login etc
  static Map<String, String> get _headers => {
        "Content-Type": "application/json",
      };

  // Headers with token for protected routes
  static Future<Map<String, String>> get _authHeaders async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString("access_token") ?? "";
    return {
      "Content-Type": "application/json",
      "Authorization": "Bearer $token",
    };
  }


  // ─────────────────────────────────────────────
  // TOKEN STORAGE
  // ─────────────────────────────────────────────

  // Save tokens after login
  static Future<void> saveTokens(
      String accessToken, String refreshToken) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString("access_token", accessToken);
    await prefs.setString("refresh_token", refreshToken);
  }

  // Clear tokens on logout
  static Future<void> clearTokens() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove("access_token");
    await prefs.remove("refresh_token");
  }

  // Check if user is already logged in
  static Future<bool> isLoggedIn() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString("access_token");
    return token != null && token.isNotEmpty;
  }


  // ─────────────────────────────────────────────
  // REGISTER
  // POST /auth/register
  // ─────────────────────────────────────────────
  static Future<Map<String, dynamic>> register({
    required String name,
    required String email,
    required String phone,
    required String password,
  }) async {
    try {
      final response = await http.post(
        Uri.parse("${AppConstants.baseUrl}${AppConstants.register}"),
        headers: _headers,
        body: jsonEncode({
          "name": name,
          "email": email,
          "phone": phone,
          "password": password,
        }),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {"success": true, "message": data["message"]};
      } else {
        String errorMessage = "Registration failed. Please try again.";
        if (data["detail"] is String) {
          errorMessage = data["detail"];
        } else if (data["detail"] is List) {
          errorMessage = data["detail"][0]["msg"]
              .toString()
              .replaceAll("Value error, ", "");
        }
        return {"success": false, "message": errorMessage};
      }
    } catch (e) {
      return {
        "success": false,
        "message": "Cannot connect to server. Please check your connection.",
      };
    }
  }


  // ─────────────────────────────────────────────
  // LOGIN
  // POST /auth/login
  // Works with email or phone number
  // Saves tokens after successful login
  // ─────────────────────────────────────────────
  static Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    try {
      // Build the request body
      // Check if the input is an email or phone number
      // If it contains @ it is an email otherwise it is a phone
      final Map<String, dynamic> body = {"password": password};

      if (email.contains("@")) {
        // User entered an email address
        body["email"] = email;
      } else {
        // User entered a phone number
        body["phone"] = email;
      }

      final response = await http.post(
        Uri.parse("${AppConstants.baseUrl}${AppConstants.login}"),
        headers: _headers,
        body: jsonEncode(body),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        // Save tokens to shared preferences
        await saveTokens(
          data["access_token"],
          data["refresh_token"],
        );

        return {
          "success": true,
          // Pass this to Flutter so it knows whether to show 2FA screen
          "two_factor_required": data["two_factor_required"] ?? false,
          "message": data["message"] ?? "Login successful",
        };
      } else {
        // Login failed — return error from backend
        String errorMessage = "Login failed. Please try again.";
        if (data["detail"] is String) {
          errorMessage = data["detail"];
        }
        return {"success": false, "message": errorMessage};
      }
    } catch (e) {
      return {
        "success": false,
        "message": "Cannot connect to server. Please check your connection.",
      };
    }
  }


  // ─────────────────────────────────────────────
  // CHECK TERMS
  // GET /terms/check
  // Called after login to decide where to navigate
  // ─────────────────────────────────────────────
  static Future<Map<String, dynamic>> checkTerms() async {
    try {
      final headers = await _authHeaders;
      final response = await http.get(
        Uri.parse("${AppConstants.baseUrl}${AppConstants.termsCheck}"),
        headers: headers,
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {
          "success": true,
          "terms_completed": data["terms_completed"],
        };
      } else {
        return {"success": false, "terms_completed": false};
      }
    } catch (e) {
      return {"success": false, "terms_completed": false};
    }
  }


  // ─────────────────────────────────────────────
  // GET TERMS STATUS
  // GET /terms/status
  // Called when terms page opens to load saved checkbox states
  // ─────────────────────────────────────────────
  static Future<Map<String, dynamic>> getTermsStatus() async {
    try {
      final headers = await _authHeaders;
      final response = await http.get(
        Uri.parse("${AppConstants.baseUrl}${AppConstants.termsStatus}"),
        headers: headers,
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        // Returns all 5 checkbox states from the database
        return {"success": true, "data": data};
      } else {
        return {
          "success": false,
          "message": data["detail"] ?? "Failed to load terms.",
        };
      }
    } catch (e) {
      return {
        "success": false,
        "message": "Cannot connect to server. Please check your connection.",
      };
    }
  }


  // ─────────────────────────────────────────────
  // SAVE TERMS
  // POST /terms/save
  // Only sends terms_of_service — the only required checkbox
  // ─────────────────────────────────────────────
  static Future<Map<String, dynamic>> saveTerms({
    required bool termsOfService,
  }) async {
    try {
      final headers = await _authHeaders;
      final response = await http.post(
        Uri.parse("${AppConstants.baseUrl}${AppConstants.termsSave}"),
        headers: headers,
        body: jsonEncode({
          "terms_of_service": termsOfService,
        }),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {"success": true, "message": data["message"]};
      } else {
        return {
          "success": false,
          "message": data["detail"] ?? "Failed to save terms.",
        };
      }
    } catch (e) {
      return {
        "success": false,
        "message": "Cannot connect to server. Please check your connection.",
      };
    }
  }


  // ─────────────────────────────────────────────
  // LOGOUT
  // POST /auth/logout
  // Blacklists the token and clears local storage
  // ─────────────────────────────────────────────
  static Future<Map<String, dynamic>> logout() async {
    try {
      final headers = await _authHeaders;
      final response = await http.post(
        Uri.parse("${AppConstants.baseUrl}${AppConstants.logout}"),
        headers: headers,
      );

      // Always clear tokens locally even if backend call fails
      await clearTokens();

      if (response.statusCode == 200) {
        return {"success": true, "message": "Logged out successfully"};
      } else {
        return {"success": true, "message": "Logged out"};
      }
    } catch (e) {
      // Clear tokens even if network fails
      await clearTokens();
      return {"success": true, "message": "Logged out"};
    }
  }


  // ─────────────────────────────────────────────
  // VERIFY OTP
  // POST /auth/verify-otp
  // ─────────────────────────────────────────────
  static Future<Map<String, dynamic>> verifyOtp({
    required String email,
    required String otp,
  }) async {
    try {
      final response = await http.post(
        Uri.parse("${AppConstants.baseUrl}${AppConstants.verifyOtp}"),
        headers: _headers,
        body: jsonEncode({"email": email, "otp": otp}),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {"success": true, "message": data["message"]};
      } else {
        return {
          "success": false,
          "message": data["detail"] ?? "OTP verification failed.",
        };
      }
    } catch (e) {
      return {
        "success": false,
        "message": "Cannot connect to server. Please check your connection.",
      };
    }
  }


  // ─────────────────────────────────────────────
  // RESEND OTP
  // POST /auth/resend-otp
  // ─────────────────────────────────────────────
  static Future<Map<String, dynamic>> resendOtp({
    required String email,
  }) async {
    try {
      final response = await http.post(
        Uri.parse(
            "${AppConstants.baseUrl}${AppConstants.resendOtp}?email=$email"),
        headers: _headers,
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {"success": true, "message": data["message"]};
      } else {
        return {
          "success": false,
          "message": data["detail"] ?? "Failed to resend OTP.",
        };
      }
    } catch (e) {
      return {
        "success": false,
        "message": "Cannot connect to server. Please check your connection.",
      };
    }
  }


  // ─────────────────────────────────────────────
  // FORGOT PASSWORD
  // POST /auth/forgot-password
  // ─────────────────────────────────────────────
  static Future<Map<String, dynamic>> forgotPassword({
    required String email,
  }) async {
    try {
      final response = await http.post(
        Uri.parse(
            "${AppConstants.baseUrl}${AppConstants.forgotPassword}"),
        headers: _headers,
        body: jsonEncode({"email": email}),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {"success": true, "message": data["message"]};
      } else {
        return {
          "success": false,
          "message": data["detail"] ?? "Failed to send reset OTP.",
        };
      }
    } catch (e) {
      return {
        "success": false,
        "message": "Cannot connect to server. Please check your connection.",
      };
    }
  }


  // ─────────────────────────────────────────────
  // RESET PASSWORD
  // POST /auth/reset-password
  // ─────────────────────────────────────────────
  static Future<Map<String, dynamic>> resetPassword({
    required String email,
    required String otp,
    required String newPassword,
    required String confirmPassword,
  }) async {
    try {
      final response = await http.post(
        Uri.parse(
            "${AppConstants.baseUrl}${AppConstants.resetPassword}"),
        headers: _headers,
        body: jsonEncode({
          "email": email,
          "otp": otp,
          "new_password": newPassword,
          "confirm_password": confirmPassword,
        }),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {"success": true, "message": data["message"]};
      } else {
        return {
          "success": false,
          "message": data["detail"] ?? "Password reset failed.",
        };
      }
    } catch (e) {
      return {
        "success": false,
        "message": "Cannot connect to server. Please check your connection.",
      };
    }
  }


  // ─────────────────────────────────────────────
  // GET PROFILE
  // GET /user/profile
  // ─────────────────────────────────────────────
  static Future<Map<String, dynamic>> getProfile() async {
    try {
      final headers = await _authHeaders;
      final response = await http.get(
        Uri.parse("${AppConstants.baseUrl}${AppConstants.profile}"),
        headers: headers,
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {"success": true, "data": data};
      } else {
        return {
          "success": false,
          "message": data["detail"] ?? "Failed to get profile.",
        };
      }
    } catch (e) {
      return {
        "success": false,
        "message": "Cannot connect to server. Please check your connection.",
      };
    }
  }
}