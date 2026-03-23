// import 'dart:convert';
// import 'dart:io';
// import 'package:http/http.dart' as http;
// import 'package:path_provider/path_provider.dart';
// import '../models/usage_summary.dart';
// import '../services/auth_storage.dart';

// class ApiService {
//   // ── Change this to your actual server IP/URL ──────────────────────
//   // If testing on a physical device with a local FastAPI server:
//   // Use your PC's local IP e.g. 'http://192.168.1.5:8000'
//   // If deployed: 'https://your-domain.com'
//   static const String baseUrl = 'http://192.168.1.5:8000';

//   // ── Usage Summary ─────────────────────────────────────────────────
//   Future<UsageSummary> fetchUsageSummary({
//     required int year,
//     required int month,
//   }) async {
//     final token = await AuthStorage.getToken();

//     final uri = Uri.parse(
//       '$baseUrl/usage/summary?year=$year&month=$month',
//     );

//     final response = await http.get(
//       uri,
//       headers: {'Authorization': 'Bearer $token'},
//     );

//     if (response.statusCode == 200) {
//       return UsageSummary.fromJson(jsonDecode(response.body));
//     } else {
//       throw Exception('Failed to load usage data: ${response.statusCode}');
//     }
//   }

//   // ── Monthly Report PDF Download ───────────────────────────────────
//   Future<File> downloadMonthlyReport({
//     required int year,
//     required int month,
//   }) async {
//     final token = await AuthStorage.getToken();

//     final uri = Uri.parse(
//       '$baseUrl/reports/monthly?year=$year&month=$month',
//     );

//     final response = await http.get(
//       uri,
//       headers: {
//         'Authorization': 'Bearer $token',
//         'Accept': 'application/pdf',
//       },
//     );

//     if (response.statusCode == 200) {
//       final dir = await getApplicationDocumentsDirectory();
//       final file = File(
//         '${dir.path}/aquasense_report_${year}_${month.toString().padLeft(2, '0')}.pdf',
//       );
//       await file.writeAsBytes(response.bodyBytes);
//       return file;
//     } else {
//       throw Exception('Failed to generate report: ${response.statusCode}');
//     }
//   }
// }

// // ## Step 4 — Check if you have `auth_storage.dart`

// // The file imports `AuthStorage` to get the JWT token. Check if you already have it:
// // ```
// // lib/services/auth_storage.dart
import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static const String baseUrl = "http://192.168.1.XX:8000";

  String? _token;

  void setToken(String token) {
    _token = token;
  }

  Map<String, String> get _headers => {
    "Content-Type": "application/json",
    "Authorization": "Bearer $_token",
  };

  // ───── Dashboard ─────
  Future<Map<String, dynamic>> getDashboardToday() async {
    final response = await http.get(
      Uri.parse("$baseUrl/mobile/dashboard/today"),
      headers: _headers,
    );
    return jsonDecode(response.body);
  }

  // ───── Zones Daily ─────
  Future<List<dynamic>> getZonesDaily() async {
    final response = await http.get(
      Uri.parse("$baseUrl/mobile/zones/daily"),
      headers: _headers,
    );
    return jsonDecode(response.body);
  }

  // ───── Flow Rate ─────
  Future<Map<String, dynamic>> getFlowRate() async {
    final response = await http.get(
      Uri.parse("$baseUrl/mobile/flowrate"),
      headers: _headers,
    );
    return jsonDecode(response.body);
  }

  // ───── Alerts ─────
  Future<Map<String, dynamic>> getAlerts() async {
    final response = await http.get(
      Uri.parse("$baseUrl/mobile/alerts"),
      headers: _headers,
    );
    return jsonDecode(response.body);
  }

  // ───── Leakages ─────
  Future<List<dynamic>> getLeakages() async {
    final response = await http.get(
      Uri.parse("$baseUrl/mobile/leakages"),
      headers: _headers,
    );
    return jsonDecode(response.body);
  }
}