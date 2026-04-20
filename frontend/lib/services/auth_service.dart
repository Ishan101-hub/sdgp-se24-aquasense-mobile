import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'auth_storage.dart';

class AuthService {
  // ── Base URLs ──────────────────────────────────────────
  static const String _host = 'https://sdgp-se24-aquasense-mobile.onrender.com';
  static const String baseUrl = '$_host/auth';
  static const _storage = FlutterSecureStorage();

  // ── Save / retrieve tokens ─────────────────────────────
  static Future<void> saveTokens(String access, String refresh) async {
    await _storage.write(key: 'access_token', value: access);
    await _storage.write(key: 'refresh_token', value: refresh);
  }

  static Future<String?> getAccessToken() => _storage.read(key: 'access_token');
  static Future<String?> getRefreshToken() =>
      _storage.read(key: 'refresh_token');

  static Future<void> clearTokens() async {
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
  }

  // ── Register ───────────────────────────────────────────
  static Future<Map<String, dynamic>> register({
    required String name,
    required String email,
    required String password,
    String? phone,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/register'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'name': name,
          'email': email,
          'password': password,
          if (phone != null && phone.isNotEmpty) 'phone': phone,
        }),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      }

      return {
        'success': false,
        'message': data['detail'] ?? 'Registration failed',
      };
    } catch (e) {
      return {
        'success': false,
        'message': 'Network error. Please check your connection.\n\nDetail: $e',
      };
    }
  }

  // ── Verify OTP (registration) ──────────────────────────
  static Future<Map<String, dynamic>> verifyOtp({
    required String email,
    required String otp,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/verify-otp'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email, 'otp': otp}),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      }

      return {
        'success': false,
        'message': data['detail'] ?? 'OTP verification failed',
      };
    } catch (e) {
      return {
        'success': false,
        'message': 'Network error. Please check your connection.\n\nDetail: $e',
      };
    }
  }

  // ── Resend OTP (registration) ──────────────────────────
  static Future<Map<String, dynamic>> resendOtp(String email) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/resend-otp?email=${Uri.encodeComponent(email)}'),
        headers: {'Content-Type': 'application/json'},
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      }

      return {
        'success': false,
        'message': data['detail'] ?? 'Failed to resend OTP',
      };
    } catch (e) {
      return {
        'success': false,
        'message': 'Network error. Please check your connection.\n\nDetail: $e',
      };
    }
  }

  // ── Login ──────────────────────────────────────────────
  static Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email, 'password': password}),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        await saveTokens(data['access_token'], data['refresh_token']);
        await AuthStorage.saveToken(data['access_token']);
        return {
          'success': true,
          'two_factor_required': data['two_factor_required'] ?? false,
          'message': data['message'] ?? '',
        };
      }

      return {'success': false, 'message': data['detail'] ?? 'Login failed'};
    } catch (e) {
      return {
        'success': false,
        'message': 'Network error. Please check your connection.\n\nDetail: $e',
      };
    }
  }

  // ── Forgot Password — send OTP ─────────────────────────
  static Future<Map<String, dynamic>> forgotPassword(String email) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/forgot-password'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email}),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      }

      return {
        'success': false,
        'message': data['detail'] ?? 'Failed to send OTP',
      };
    } catch (e) {
      return {
        'success': false,
        'message': 'Network error. Please check your connection.\n\nDetail: $e',
      };
    }
  }

  // ── Reset Password — verify OTP + set new password ────
  static Future<Map<String, dynamic>> resetPassword({
    required String email,
    required String otp,
    required String newPassword,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/reset-password'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': email,
          'otp': otp,
          'new_password': newPassword,
          'confirm_password': newPassword,
        }),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      }

      return {
        'success': false,
        'message': data['detail'] ?? 'Password reset failed',
      };
    } catch (e) {
      return {
        'success': false,
        'message': 'Network error. Please check your connection.\n\nDetail: $e',
      };
    }
  }

  // ── Logout ─────────────────────────────────────────────
  static Future<void> logout() async {
    try {
      final token = await getAccessToken();
      if (token != null) {
        await http.post(
          Uri.parse('$baseUrl/logout'),
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer $token',
          },
        );
      }
    } catch (_) {
      // Silently fail — still clear local tokens
    } finally {
      await clearTokens();
    }
  }

  // ── Get My District ────────────────────────────────────
  static Future<Map<String, dynamic>> getMyDistrict() async {
    try {
      final token = await getAccessToken();
      final response = await http
          .get(
            Uri.parse('$_host/district/my-district'),
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
            },
          )
          .timeout(const Duration(seconds: 10));

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'district': data['district']};
      }

      return {
        'success': false,
        'message': data['detail'] ?? 'Failed to load district',
      };
    } catch (e) {
      return {'success': false, 'message': 'Error: $e'};
    }
  }

  // ── Save District ───────────────────────────────────────
  static Future<Map<String, dynamic>> saveDistrict(String district) async {
    try {
      final token = await getAccessToken();
      final response = await http
          .post(
            Uri.parse('$_host/district/save'),
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
            },
            body: jsonEncode({'district': district}),
          )
          .timeout(const Duration(seconds: 10));

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {
          'success': true,
          'message': data['message'],
          'district': data['district'],
        };
      }

      return {
        'success': false,
        'message': data['detail'] ?? 'Failed to save district',
      };
    } catch (e) {
      return {'success': false, 'message': 'Error: $e'};
    }
  }

  // ── Get Profile ────────────────────────────────────────
  static Future<Map<String, dynamic>> getProfile() async {
    try {
      final token = await getAccessToken();
      final response = await http
          .get(
            Uri.parse('$_host/user/profile'),
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
            },
          )
          .timeout(const Duration(seconds: 10));

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, ...data};
      }

      return {
        'success': false,
        'message': data['detail'] ?? 'Failed to load profile',
      };
    } catch (e) {
      return {'success': false, 'message': 'Error: $e'};
    }
  }

  // ── Update Profile ─────────────────────────────────────
  static Future<Map<String, dynamic>> updateProfile({
    String? name,
    String? phone,
    String? address,
    String? profilePicture,
  }) async {
    try {
      final token = await getAccessToken();

      final body = <String, dynamic>{};
      if (name != null) body['name'] = name;
      if (phone != null) body['phone'] = phone;
      if (address != null) body['address'] = address;
      if (profilePicture != null) body['profile_picture'] = profilePicture;

      final response = await http
          .put(
            Uri.parse('$_host/user/update-profile'),
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
            },
            body: jsonEncode(body),
          )
          .timeout(const Duration(seconds: 10));

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      }

      return {
        'success': false,
        'message': data['detail'] ?? 'Failed to update profile',
      };
    } catch (e) {
      return {'success': false, 'message': 'Error: $e'};
    }
  }

  // ── Delete Account ─────────────────────────────────────
  static Future<Map<String, dynamic>> deleteAccount() async {
    try {
      final token = await getAccessToken();
      final response = await http
          .delete(
            Uri.parse('$_host/user/delete-account'),
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
            },
          )
          .timeout(const Duration(seconds: 10));

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        await clearTokens();
        return {'success': true, 'message': data['message']};
      }

      return {
        'success': false,
        'message': data['detail'] ?? 'Failed to delete account',
      };
    } catch (e) {
      return {'success': false, 'message': 'Error: $e'};
    }
  }

  // ── Verify 2FA after login ─────────────────────────────
  static Future<Map<String, dynamic>> verify2FALogin(String otp) async {
    try {
      final token = await getAccessToken();
      final response = await http
          .post(
            Uri.parse('$baseUrl/2fa/verify-login'),
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
            },
            body: jsonEncode({'otp': otp}),
          )
          .timeout(const Duration(seconds: 10));

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      }

      return {
        'success': false,
        'message': data['detail'] ?? '2FA verification failed',
      };
    } catch (e) {
      return {'success': false, 'message': 'Error: $e'};
    }
  }

  // ── Get Security Settings ──────────────────────────────
  static Future<Map<String, dynamic>> getSecuritySettings() async {
    try {
      final token = await getAccessToken();
      final response = await http
          .get(
            Uri.parse('$_host/security/settings'),
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
            },
          )
          .timeout(const Duration(seconds: 10));

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {
          'success': true,
          'two_factor_enabled': data['two_factor_enabled'],
          'login_alerts_enabled': data['login_alerts_enabled'],
          'auto_lock_minutes': data['auto_lock_minutes'],
        };
      }

      return {
        'success': false,
        'message': data['detail'] ?? 'Failed to load settings',
      };
    } catch (e) {
      return {'success': false, 'message': 'Error: $e'};
    }
  }

  // ── Enable 2FA — sends OTP to email ───────────────────
  static Future<Map<String, dynamic>> enable2FA() async {
    try {
      final token = await getAccessToken();
      final response = await http
          .post(
            Uri.parse('$_host/security/2fa/enable'),
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
            },
          )
          .timeout(const Duration(seconds: 10));

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      }

      return {
        'success': false,
        'message': data['detail'] ?? 'Failed to enable 2FA',
      };
    } catch (e) {
      return {'success': false, 'message': 'Error: $e'};
    }
  }

  // ── Verify Enable 2FA — submit OTP ────────────────────
  static Future<Map<String, dynamic>> verifyEnable2FA(String otp) async {
    try {
      final token = await getAccessToken();
      final response = await http
          .post(
            Uri.parse('$_host/security/2fa/verify-enable'),
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
            },
            body: jsonEncode({'otp': otp}),
          )
          .timeout(const Duration(seconds: 10));

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      }

      return {
        'success': false,
        'message': data['detail'] ?? 'OTP verification failed',
      };
    } catch (e) {
      return {'success': false, 'message': 'Error: $e'};
    }
  }

  // ── Disable 2FA — requires password ───────────────────
  static Future<Map<String, dynamic>> disable2FA(String password) async {
    try {
      final token = await getAccessToken();
      final response = await http
          .post(
            Uri.parse('$_host/security/2fa/disable'),
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
            },
            body: jsonEncode({'password': password}),
          )
          .timeout(const Duration(seconds: 10));

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      }

      return {
        'success': false,
        'message': data['detail'] ?? 'Failed to disable 2FA',
      };
    } catch (e) {
      return {'success': false, 'message': 'Error: $e'};
    }
  }

  // ── Set Auto Lock ──────────────────────────────────────
  static Future<Map<String, dynamic>> setAutoLock(int minutes) async {
    try {
      final token = await getAccessToken();
      final response = await http
          .post(
            Uri.parse('$_host/security/auto-lock'),
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
            },
            body: jsonEncode({'minutes': minutes}),
          )
          .timeout(const Duration(seconds: 10));

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      }

      return {
        'success': false,
        'message': data['detail'] ?? 'Failed to update auto lock',
      };
    } catch (e) {
      return {'success': false, 'message': 'Error: $e'};
    }
  }

  // ── Toggle Login Alerts ────────────────────────────────
  static Future<Map<String, dynamic>> toggleLoginAlerts(bool enabled) async {
    try {
      final token = await getAccessToken();
      final response = await http
          .post(
            Uri.parse('$_host/security/login-alerts'),
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
            },
            body: jsonEncode({'enabled': enabled}),
          )
          .timeout(const Duration(seconds: 10));

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      }

      return {
        'success': false,
        'message': data['detail'] ?? 'Failed to update login alerts',
      };
    } catch (e) {
      return {'success': false, 'message': 'Error: $e'};
    }
  }

  // ── Save Terms ─────────────────────────────────────────
  static Future<Map<String, dynamic>> saveTerms() async {
    try {
      final token = await getAccessToken();

      if (token == null || token.isEmpty) {
        return {
          'success': false,
          'message': 'You are not logged in. Please log in and try again.',
        };
      }

      final response = await http
          .post(
            Uri.parse('$_host/terms/save'),
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer $token',
            },
            body: jsonEncode({'terms_of_service': true}),
          )
          .timeout(
            const Duration(seconds: 10),
            onTimeout: () =>
                throw Exception('Request timed out. Please try again.'),
          );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      }

      if (response.statusCode == 401) {
        return {
          'success': false,
          'message': 'Session expired. Please log in again.',
        };
      }

      return {
        'success': false,
        'message':
            data['detail'] ?? 'Failed to save terms. (${response.statusCode})',
      };
    } catch (e) {
      return {'success': false, 'message': 'Error: $e'};
    }
  }

  // ── Authenticated GET ──────────────────────────────────
  static Future<http.Response> authGet(String endpoint) async {
    final token = await getAccessToken();
    return await http.get(
      Uri.parse('$_host$endpoint'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
    );
  }

  // ── Authenticated POST ─────────────────────────────────
  static Future<http.Response> authPost(
    String endpoint,
    Map<String, dynamic> body,
  ) async {
    final token = await getAccessToken();
    return await http.post(
      Uri.parse('$_host$endpoint'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(body),
    );
  }
}
