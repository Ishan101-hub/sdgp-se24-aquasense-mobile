import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class AuthService {
  static const String baseUrl = 'http://localhost:8000/auth';
  static const _storage = FlutterSecureStorage();

  // ── Save / retrieve tokens ─────────────────────────────
  static Future<void> saveTokens(String access, String refresh) async {
    await _storage.write(key: 'access_token', value: access);
    await _storage.write(key: 'refresh_token', value: refresh);
  }

  static Future<String?> getAccessToken() => _storage.read(key: 'access_token');
  static Future<String?> getRefreshToken() => _storage.read(key: 'refresh_token');

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

      return {'success': false, 'message': data['detail'] ?? 'Registration failed'};
    } catch (e) {
      return {'success': false, 'message': 'Network error. Please check your connection.\n\nDetail: $e'};
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

      return {'success': false, 'message': data['detail'] ?? 'OTP verification failed'};
    } catch (e) {
      return {'success': false, 'message': 'Network error. Please check your connection.\n\nDetail: $e'};
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

      return {'success': false, 'message': data['detail'] ?? 'Failed to resend OTP'};
    } catch (e) {
      return {'success': false, 'message': 'Network error. Please check your connection.\n\nDetail: $e'};
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
        return {
          'success': true,
          'two_factor_required': data['two_factor_required'] ?? false,
          'message': data['message'] ?? '',
        };
      }

      return {'success': false, 'message': data['detail'] ?? 'Login failed'};
    } catch (e) {
      return {'success': false, 'message': 'Network error. Please check your connection.\n\nDetail: $e'};
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

      return {'success': false, 'message': data['detail'] ?? 'Failed to send OTP'};
    } catch (e) {
      return {'success': false, 'message': 'Network error. Please check your connection.\n\nDetail: $e'};
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
        }),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        return {'success': true, 'message': data['message']};
      }

      return {'success': false, 'message': data['detail'] ?? 'Password reset failed'};
    } catch (e) {
      return {'success': false, 'message': 'Network error. Please check your connection.\n\nDetail: $e'};
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

  // ── Authenticated GET ──────────────────────────────────
  static Future<http.Response> authGet(String endpoint) async {
    final token = await getAccessToken();
    return await http.get(
      Uri.parse('http://localhost:8000$endpoint'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
    );
  }

  // ── Authenticated POST ─────────────────────────────────
  static Future<http.Response> authPost(
      String endpoint, Map<String, dynamic> body) async {
    final token = await getAccessToken();
    return await http.post(
      Uri.parse('http://localhost:8000$endpoint'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(body),
    );
  }
}