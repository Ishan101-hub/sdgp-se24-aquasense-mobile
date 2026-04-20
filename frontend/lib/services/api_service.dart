// lib/services/api_service.dart
// AquaSense — centralised HTTP client for all backend calls.
// All /mobile/* endpoints from mobile_router.py are implemented here.

import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

import '../models/usage_summary.dart';
import '../models/app_notification.dart';
import '../models/mobile_models.dart';
import '../services/auth_storage.dart';

class ApiService {
  // ── Server URL ────────────────────────────────────────────────────────────
  // Same WiFi (real device): 'http://192.168.x.x:8000'
  // Android emulator:        'http://10.0.2.2:8000'
  // Deployed:                'https://your-app.onrender.com'
  static const String baseUrl =
      'https://sdgp-se24-aquasense-mobile.onrender.com';
  // ── Shared header builder ─────────────────────────────────────────────────
  Future<Map<String, String>> _authHeaders({String? accept}) async {
    final token = await AuthStorage.getToken();
    return {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
      if (accept != null) 'Accept': accept,
    };
  }

  // ── Generic error helper ──────────────────────────────────────────────────
  // Extracts the FastAPI `detail` field from error responses when available.
  String _errorDetail(http.Response res, String fallback) {
    try {
      final body = jsonDecode(res.body) as Map<String, dynamic>;
      return body['detail'] as String? ?? fallback;
    } catch (_) {
      return fallback;
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  /mobile/zones/daily   →  DailyConsumptionCard + TodayCard zones
  // ══════════════════════════════════════════════════════════════════════════

  Future<List<ZoneDaily>> fetchZonesDaily({int? networkId}) async {
    final uri = Uri.parse('$baseUrl/mobile/zones/daily').replace(
      queryParameters: networkId != null
          ? {'network_id': networkId.toString()}
          : null,
    );
    final response = await http
        .get(uri, headers: await _authHeaders())
        .timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List<dynamic>;
      return data
          .map((z) => ZoneDaily.fromJson(z as Map<String, dynamic>))
          .toList();
    } else if (response.statusCode == 404) {
      return []; // no network registered yet
    }
    throw Exception(
      _errorDetail(response, 'Failed to load zones (${response.statusCode})'),
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  /mobile/flowrate   →  WaterStatusCard
  // ══════════════════════════════════════════════════════════════════════════

  Future<FlowRateData> fetchFlowRate({int? networkId}) async {
    final uri = Uri.parse('$baseUrl/mobile/flowrate').replace(
      queryParameters: networkId != null
          ? {'network_id': networkId.toString()}
          : null,
    );
    final response = await http
        .get(uri, headers: await _authHeaders())
        .timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      return FlowRateData.fromJson(
        jsonDecode(response.body) as Map<String, dynamic>,
      );
    } else if (response.statusCode == 404) {
      return FlowRateData.empty();
    }
    throw Exception(
      _errorDetail(
        response,
        'Failed to load flow rate (${response.statusCode})',
      ),
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  /mobile/dashboard/today   →  TodayCard totals
  // ══════════════════════════════════════════════════════════════════════════

  Future<DashboardToday> fetchDashboardToday({int? networkId}) async {
    final uri = Uri.parse('$baseUrl/mobile/dashboard/today').replace(
      queryParameters: networkId != null
          ? {'network_id': networkId.toString()}
          : null,
    );
    final response = await http
        .get(uri, headers: await _authHeaders())
        .timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      return DashboardToday.fromJson(
        jsonDecode(response.body) as Map<String, dynamic>,
      );
    } else if (response.statusCode == 404) {
      return DashboardToday.empty();
    }
    throw Exception(
      _errorDetail(
        response,
        'Failed to load dashboard (${response.statusCode})',
      ),
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  /mobile/leakages   →  Leakages screen
  // ══════════════════════════════════════════════════════════════════════════

  Future<List<LeakageZone>> fetchLeakages({int? networkId}) async {
    final uri = Uri.parse('$baseUrl/mobile/leakages').replace(
      queryParameters: networkId != null
          ? {'network_id': networkId.toString()}
          : null,
    );
    final response = await http
        .get(uri, headers: await _authHeaders())
        .timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List<dynamic>;
      return data
          .map((z) => LeakageZone.fromJson(z as Map<String, dynamic>))
          .toList();
    } else if (response.statusCode == 404) {
      return [];
    }
    throw Exception(
      _errorDetail(
        response,
        'Failed to load leakages (${response.statusCode})',
      ),
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  POST /mobile/valve   →  Leakages screen valve toggle
  // ══════════════════════════════════════════════════════════════════════════

  /// Returns a description of what happened (e.g. "commands_sent").
  /// Throws a descriptive exception on conflict (active leak) or error.
  Future<Map<String, dynamic>> sendValveCommand(ValveCommand cmd) async {
    final uri = Uri.parse('$baseUrl/mobile/valve');
    final response = await http
        .post(
          uri,
          headers: await _authHeaders(),
          body: jsonEncode(cmd.toJson()),
        )
        .timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else if (response.statusCode == 409) {
      // Active leak — backend wants the user to resolve the alert first.
      throw Exception(
        _errorDetail(
          response,
          'Active leak detected. Resolve the alert first.',
        ),
      );
    }
    throw Exception(
      _errorDetail(response, 'Valve command failed (${response.statusCode})'),
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  /mobile/report/monthly   →  Report screen
  // ══════════════════════════════════════════════════════════════════════════

  Future<MonthlyReport> fetchMonthlyReport({
    required int year,
    required int month,
    int? networkId,
  }) async {
    final params = <String, String>{
      'year': year.toString(),
      'month': month.toString(),
      if (networkId != null) 'network_id': networkId.toString(),
    };
    final uri = Uri.parse(
      '$baseUrl/mobile/report/monthly',
    ).replace(queryParameters: params);
    final response = await http
        .get(uri, headers: await _authHeaders())
        .timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      return MonthlyReport.fromJson(
        jsonDecode(response.body) as Map<String, dynamic>,
      );
    } else if (response.statusCode == 404) {
      return MonthlyReport.empty(year, month);
    }
    throw Exception(
      _errorDetail(response, 'Failed to load report (${response.statusCode})'),
    );
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  GET /mobile/alerts   →  Notification bell count + list
  // ══════════════════════════════════════════════════════════════════════════

  Future<AlertsResponse> fetchAlerts({
    bool resolved = false,
    int limit = 50,
    int? networkId,
  }) async {
    final params = <String, String>{
      'resolved': resolved.toString(),
      'limit': limit.toString(),
      if (networkId != null) 'network_id': networkId.toString(),
    };
    final uri = Uri.parse(
      '$baseUrl/mobile/alerts',
    ).replace(queryParameters: params);
    final response = await http
        .get(uri, headers: await _authHeaders())
        .timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      return AlertsResponse.fromJson(
        jsonDecode(response.body) as Map<String, dynamic>,
      );
    }
    return AlertsResponse.empty();
  }

  // Convenience: only the badge count (avoids deserializing all items).
  Future<int> fetchUnresolvedAlertCount({int? networkId}) async {
    final res = await fetchAlerts(
      resolved: false,
      limit: 1,
      networkId: networkId,
    );
    return res.unreadCount;
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  POST /mobile/alerts/{id}/resolve
  // ══════════════════════════════════════════════════════════════════════════

  Future<void> resolveAlert(int alertId) async {
    final uri = Uri.parse('$baseUrl/mobile/alerts/$alertId/resolve');
    final response = await http
        .post(uri, headers: await _authHeaders())
        .timeout(const Duration(seconds: 10));

    if (response.statusCode != 200) {
      throw Exception(
        _errorDetail(
          response,
          'Failed to resolve alert (${response.statusCode})',
        ),
      );
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  GET /mobile/notifications   →  BellButton notification list
  // ══════════════════════════════════════════════════════════════════════════

  Future<List<MobileNotification>> fetchNotifications({int? networkId}) async {
    final uri = Uri.parse('$baseUrl/mobile/notifications').replace(
      queryParameters: networkId != null
          ? {'network_id': networkId.toString()}
          : null,
    );
    final response = await http
        .get(uri, headers: await _authHeaders())
        .timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as List<dynamic>;
      return data
          .map((n) => MobileNotification.fromJson(n as Map<String, dynamic>))
          .toList();
    }
    return [];
  }

  // ══════════════════════════════════════════════════════════════════════════
  //  KEPT FROM ORIGINAL: Usage Summary  +  Monthly Report PDF download
  // ══════════════════════════════════════════════════════════════════════════

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
    }
    throw Exception('Failed to load usage data: ${response.statusCode}');
  }

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
      final name =
          'aquasense_report_${year}_${month.toString().padLeft(2, '0')}.pdf';
      final file = File('${dir.path}/$name');
      await file.writeAsBytes(response.bodyBytes);
      return file;
    }
    throw Exception('Failed to download report: ${response.statusCode}');
  }
}
