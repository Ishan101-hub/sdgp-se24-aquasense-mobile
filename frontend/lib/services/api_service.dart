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
