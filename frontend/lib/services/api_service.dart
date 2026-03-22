import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/usage_summary.dart';
import 'dart:io';
import 'package:path_provider/path_provider.dart';

class ApiService {
  // ── Change this to your FastAPI server IP ──
  // Physical device + local PC: use your PC's WiFi IP e.g. 192.168.1.5
  // Deployed server: use your domain e.g. https://aquasense.com
  static const String baseUrl = 'http://192.168.1.10:8000';

  // ── Get saved JWT token ───
  Future<String?> _getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('auth_token');
  }

  // ── Fetch usage summary from backend ───
  Future<UsageSummary> fetchUsageSummary({
    required int year,
    required int month,
  }) async {
    final token = await _getToken();

    final uri = Uri.parse('$baseUrl/usage/summary?year=$year&month=$month');

    final response = await http.get(
      uri,
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      return UsageSummary.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to load usage data: ${response.statusCode}');
    }
  }
  // ── Fetch unresolved alert count ───
Future<int> fetchUnresolvedAlertCount() async {
  final token = await _getToken();

  final uri = Uri.parse('$baseUrl/alerts/unresolved-count');

  final response = await http.get(
    uri,
    headers: {'Authorization': 'Bearer $token'},
  );

  if (response.statusCode == 200) {
    final data = jsonDecode(response.body);
    return (data['count'] as num).toInt();
  } else {
    throw Exception('Failed to load alert count: ${response.statusCode}');
  }
}

// ── Download monthly PDF report ───
Future<File> downloadMonthlyReport({
  required int year,
  required int month,
}) async {
  final token = await _getToken();

  final uri = Uri.parse('$baseUrl/usage/report?year=$year&month=$month');

  final response = await http.get(
    uri,
    headers: {'Authorization': 'Bearer $token'},
  );

  if (response.statusCode == 200) {
    // Save PDF to temp directory
    final dir = await getTemporaryDirectory();
    final file = File('${dir.path}/report_${year}_$month.pdf');
    await file.writeAsBytes(response.bodyBytes);
    return file;
  } else {
    throw Exception('Failed to download report: ${response.statusCode}');
  }
}
}
