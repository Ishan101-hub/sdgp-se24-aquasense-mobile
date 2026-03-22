import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

import '../models/usage_summary.dart';
import '../models/app_notification.dart';
import '../services/auth_storage.dart'; // Ensure this file exists for token management

class ApiService {
  // Use the IP address where your FastAPI server is currently running
  static const String baseUrl = 'http://192.168.8.171:8000';

  // ── Shared header builder ─────────────────────────────────────────────────
  // This prevents repeating the Token and Content-Type logic in every method.
  Future<Map<String, String>> _authHeaders({String? accept}) async {
    final token = await AuthStorage.getToken();
    return {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
      if (accept != null) 'Accept': accept,
    };
  }

  // ── Usage Summary (Usage Screen) ──────────────────────────────────────────
  Future<UsageSummary> fetchUsageSummary({
    required int year,
    required int month,
  }) async {
    final uri = Uri.parse('$baseUrl/usage/summary?year=$year&month=$month');
    final response = await http.get(uri, headers: await _authHeaders());

    if (response.statusCode == 200) {
      return UsageSummary.fromJson(jsonDecode(response.body));
    } else if (response.statusCode == 404) {
      return UsageSummary.empty(year, month);
    } else {
      throw Exception('Failed to load usage data: ${response.statusCode}');
    }
  }

  // ── Notification Bell Badge Count ────────────────────────────────────────
  Future<int> fetchUnresolvedAlertCount() async {
    final uri = Uri.parse('$baseUrl/mobile/alerts?resolved=false&limit=1');
    final response = await http.get(uri, headers: await _authHeaders());

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      // Using 'unread_count' as per your second snippet logic
      return (data['unread_count'] as num? ?? 0).toInt();
    }
    return 0; 
  }

  // ── Notifications List (Bell Button) ─────────────────────────────────────
  Future<List<AppNotification>> fetchNotifications() async {
    final uri = Uri.parse('$baseUrl/mobile/notifications');
    final response = await http.get(uri, headers: await _authHeaders());

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List<dynamic>;
      return data
          .map((n) => AppNotification.fromJson(n as Map<String, dynamic>))
          .toList();
    }
    return []; 
  }

  // ── Monthly Report PDF Download ──────────────────────────────────────────
  Future<File> downloadMonthlyReport({
    required int year,
    required int month,
  }) async {
    final uri = Uri.parse('$baseUrl/reports/monthly?year=$year&month=$month');
    final response = await http.get(
      uri,
      headers: await _authHeaders(accept: 'application/pdf'),
    );

    if (response.statusCode == 200) {
      final dir = await getApplicationDocumentsDirectory();
      final name = 'aquasense_report_${year}_${month.toString().padLeft(2, '0')}.pdf';
      final file = File('${dir.path}/$name');
      await file.writeAsBytes(response.bodyBytes);
      return file;
    } else {
      throw Exception('Failed to download report: ${response.statusCode}');
    }
  }
}