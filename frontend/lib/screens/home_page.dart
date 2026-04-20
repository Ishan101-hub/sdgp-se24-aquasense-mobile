// import 'dart:async';
// import 'package:flutter/material.dart';

// import '../models/mobile_models.dart';
// import '../services/api_service.dart';
// import '../widgets/today_card.dart';
// import '../widgets/water_status_card.dart';
// import '../widgets/daily_consumption_card.dart';
// import '../widgets/usage_chart_card.dart';
// import '../widgets/usage_summary_card.dart';

// class HomePage extends StatefulWidget {
//   final void Function(int tabIndex) onSwitchTab;

//   const HomePage({super.key, required this.onSwitchTab});

//   @override
//   State<HomePage> createState() => _HomePageState();
// }

// class _HomePageState extends State<HomePage> {
//   final _api = ApiService();

//   bool   _isLoading = true;
//   String? _error;

//   // Live data from backend
//   List<ZoneDaily> _zones         = [];
//   FlowRateData    _flowRate      = FlowRateData.empty();
//   DashboardToday  _dashboardToday = DashboardToday.empty();

//   Timer? _timer;

//   @override
//   void initState() {
//     super.initState();
//     _fetchData();
//     // Refresh every 10 seconds — matches ESP32 → MQTT → FastAPI pipeline
//     _timer = Timer.periodic(const Duration(seconds: 10), (_) => _fetchData());
//   }

//   @override
//   void dispose() {
//     _timer?.cancel();
//     super.dispose();
//   }

//   Future<void> _fetchData() async {
//     try {
//       // All three endpoints in parallel for speed
//       final results = await Future.wait([
//         _api.fetchZonesDaily(),
//         _api.fetchFlowRate(),
//         _api.fetchDashboardToday(),
//       ]);

//       if (mounted) {
//         setState(() {
//           _zones          = results[0] as List<ZoneDaily>;
//           _flowRate       = results[1] as FlowRateData;
//           _dashboardToday = results[2] as DashboardToday;
//           _isLoading      = false;
//           _error          = null;
//         });
//       }
//     } catch (e) {
//       if (mounted) {
//         setState(() {
//           _isLoading = false;
//           _error     = 'Failed to load data.\nCheck your connection.';
//         });
//       }
//     }
//   }

//   @override
//   Widget build(BuildContext context) {
//     final isDark = Theme.of(context).brightness == Brightness.dark;

//     // ── Loading state ──────────────────────────────────────────────────────
//     if (_isLoading) {
//       return Scaffold(
//         backgroundColor:
//             isDark ? const Color(0xFF121212) : const Color(0xFFEEF4FF),
//         body: const Center(
//           child: CircularProgressIndicator(color: Color(0xFF1A1A6E)),
//         ),
//       );
//     }

//     // ── Error state ────────────────────────────────────────────────────────
//     if (_error != null) {
//       return Scaffold(
//         backgroundColor:
//             isDark ? const Color(0xFF121212) : const Color(0xFFEEF4FF),
//         body: Center(
//           child: Column(
//             mainAxisAlignment: MainAxisAlignment.center,
//             children: [
//               const Icon(Icons.wifi_off, size: 60, color: Colors.grey),
//               const SizedBox(height: 16),
//               Text(
//                 _error!,
//                 textAlign: TextAlign.center,
//                 style: const TextStyle(color: Colors.grey, fontSize: 14),
//               ),
//               const SizedBox(height: 20),
//               ElevatedButton.icon(
//                 onPressed: () {
//                   setState(() {
//                     _isLoading = true;
//                     _error     = null;
//                   });
//                   _fetchData();
//                 },
//                 icon:  const Icon(Icons.refresh),
//                 label: const Text('Retry'),
//                 style: ElevatedButton.styleFrom(
//                   backgroundColor: const Color(0xFF1A1A6E),
//                   foregroundColor: Colors.white,
//                 ),
//               ),
//             ],
//           ),
//         ),
//       );
//     }

//     // ── Map ZoneDaily → WaterZone (used by DailyConsumptionCard) ──────────
//     final List<WaterZone> waterZones = _zones
//         .map((z) => WaterZone(name: z.name, used: z.used, average: z.average))
//         .toList();

//     // ── Totals from /mobile/dashboard/today (server-computed, accurate) ───
//     final double litresUsed   = _dashboardToday.litresUsed;
//     final double dailyAverage = _dashboardToday.dailyAverage;
//     final double percent      = _dashboardToday.percent;

//     // ── Fallback totals from zones if dashboard returns zeros ─────────────
//     final double zonesTotal   = _zones.fold(0, (s, z) => s + z.used);
//     final double zonesAverage = _zones.fold(0, (s, z) => s + z.average);

//     final double displayUsed    = litresUsed   > 0 ? litresUsed   : zonesTotal;
//     final double displayAverage = dailyAverage > 0 ? dailyAverage : zonesAverage;
//     final double displayPercent = percent      > 0 ? percent
//         : (displayAverage > 0
//             ? (displayUsed / displayAverage * 100).clamp(0, 999)
//             : 0);

//     return Scaffold(
//       backgroundColor:
//           isDark ? const Color(0xFF121212) : const Color(0xFFEEF4FF),
//       // No BellButton — notification FAB lives in HomeScreen (shell level)
//       // so it stays visible regardless of which tab is active.
//       body: SafeArea(
//         child: SingleChildScrollView(
//           padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
//           child: Column(
//             children: [

//               IntrinsicHeight(
//                 child: Row(
//                   crossAxisAlignment: CrossAxisAlignment.stretch,
//                   children: [

//                     // TodayCard — server-computed totals with zone-level fallback
//                     Expanded(
//                       child: TodayCard(
//                         litresUsed:          displayUsed,
//                         dailyAverageLitres:  displayAverage,
//                         dailyAveragePercent: displayPercent,
//                       ),
//                     ),

//                     const SizedBox(width: 12),

//                     // WaterStatusCard — live flow rate from /mobile/flowrate
//                     Expanded(
//                       child: WaterStatusCard(
//                         flowRate: _flowRate.flowRate,
//                       ),
//                     ),

//                   ],
//                 ),
//               ),

//               const SizedBox(height: 16),

//               // DailyConsumptionCard — per-zone breakdown from /mobile/zones/daily
//               DailyConsumptionCard(zones: waterZones),

//               const SizedBox(height: 16),

//               // UsageChartCard — today's total drives the daily spot
//               UsageChartCard(todayUsage: displayUsed),

//               const SizedBox(height: 16),

//               // UsageSummaryCard — derived from dashboard totals
//               UsageSummaryCard(
//                 dailyAverage:       displayAverage,
//                 dailyConsumption:   displayUsed,
//                 weeklyAverage:      displayAverage * 7,
//                 weeklyConsumption:  displayUsed    * 7,
//                 monthlyAverage:     displayAverage * 30,
//                 monthlyConsumption: displayUsed    * 30,
//               ),

//             ],
//           ),
//         ),
//       ),
//     );
//   }
// }

// lib/screens/home_page.dart
// AquaSense — Home tab.
// Fetches live data from /mobile/zones/daily, /mobile/flowrate, and
// /mobile/dashboard/today via ApiService. Refreshes every 10 seconds.
//
// NOTE: BellButton has been removed. Notifications are handled by the
// shell-level FAB in home_screen.dart so they are visible on all tabs.

import 'dart:async';
import 'package:flutter/material.dart';

import '../models/mobile_models.dart';
import '../services/api_service.dart';
import '../widgets/today_card.dart';
import '../widgets/water_status_card.dart';
import '../widgets/daily_consumption_card.dart';
import '../widgets/usage_chart_card.dart';
import '../widgets/usage_summary_card.dart';

class HomePage extends StatefulWidget {
  final void Function(int tabIndex) onSwitchTab;

  const HomePage({super.key, required this.onSwitchTab});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final _api = ApiService();

  bool   _isLoading = true;
  String? _error;

  // Live data from backend
  List<ZoneDaily> _zones         = [];
  FlowRateData    _flowRate      = FlowRateData.empty();
  DashboardToday  _dashboardToday = DashboardToday.empty();

  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _fetchData();
    // Refresh every 10 seconds — matches ESP32 → MQTT → FastAPI pipeline
    _timer = Timer.periodic(const Duration(seconds: 10), (_) => _fetchData());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _fetchData() async {
    try {
      // All three endpoints in parallel for speed
      final results = await Future.wait([
        _api.fetchZonesDaily(),
        _api.fetchFlowRate(),
        _api.fetchDashboardToday(),
      ]);

      if (mounted) {
        setState(() {
          _zones          = results[0] as List<ZoneDaily>;
          _flowRate       = results[1] as FlowRateData;
          _dashboardToday = results[2] as DashboardToday;
          _isLoading      = false;
          _error          = null;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _error     = 'Failed to load data.\nCheck your connection.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    // ── Loading state ──────────────────────────────────────────────────────
    if (_isLoading) {
      return Scaffold(
        backgroundColor:
            isDark ? const Color(0xFF121212) : const Color(0xFFEEF4FF),
        body: const Center(
          child: CircularProgressIndicator(color: Color(0xFF1A1A6E)),
        ),
      );
    }

    // ── Error state ────────────────────────────────────────────────────────
    if (_error != null) {
      return Scaffold(
        backgroundColor:
            isDark ? const Color(0xFF121212) : const Color(0xFFEEF4FF),
        body: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.wifi_off, size: 60, color: Colors.grey),
              const SizedBox(height: 16),
              Text(
                _error!,
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.grey, fontSize: 14),
              ),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: () {
                  setState(() {
                    _isLoading = true;
                    _error     = null;
                  });
                  _fetchData();
                },
                icon:  const Icon(Icons.refresh),
                label: const Text('Retry'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF1A1A6E),
                  foregroundColor: Colors.white,
                ),
              ),
            ],
          ),
        ),
      );
    }

    // ── Map ZoneDaily → WaterZone (used by DailyConsumptionCard) ──────────
    final List<WaterZone> waterZones = _zones
        .map((z) => WaterZone(name: z.name, used: z.used, average: z.average))
        .toList();

    // ── Totals from /mobile/dashboard/today (server-computed, accurate) ───
    final double litresUsed   = _dashboardToday.litresUsed;
    final double dailyAverage = _dashboardToday.dailyAverage;
    final double percent      = _dashboardToday.percent;

    // ── Fallback totals from zones if dashboard returns zeros ─────────────
    final double zonesTotal   = _zones.fold(0, (s, z) => s + z.used);
    final double zonesAverage = _zones.fold(0, (s, z) => s + z.average);

    final double displayUsed    = litresUsed   > 0 ? litresUsed   : zonesTotal;
    final double displayAverage = dailyAverage > 0 ? dailyAverage : zonesAverage;
    final double displayPercent = percent      > 0 ? percent
        : (displayAverage > 0
            ? (displayUsed / displayAverage * 100).clamp(0, 999)
            : 0);

    return Scaffold(
      backgroundColor:
          isDark ? const Color(0xFF121212) : const Color(0xFFEEF4FF),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
          child: Column(
            children: [

              IntrinsicHeight(
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [

                    // TodayCard — server-computed totals with zone-level fallback
                    Expanded(
                      child: TodayCard(
                        litresUsed:          displayUsed,
                        dailyAverageLitres:  displayAverage,
                        dailyAveragePercent: displayPercent,
                      ),
                    ),

                    const SizedBox(width: 12),

                    // WaterStatusCard — live flow rate from /mobile/flowrate
                    Expanded(
                      child: WaterStatusCard(
                        flowRate: _flowRate.flowRate,
                      ),
                    ),

                  ],
                ),
              ),

              const SizedBox(height: 16),

              // DailyConsumptionCard — per-zone breakdown from /mobile/zones/daily
              DailyConsumptionCard(zones: waterZones),

              const SizedBox(height: 16),

              // UsageChartCard — today's total drives the daily spot
              UsageChartCard(todayUsage: displayUsed),

              const SizedBox(height: 16),

              // UsageSummaryCard — derived from dashboard totals
              UsageSummaryCard(
                dailyAverage:       displayAverage,
                dailyConsumption:   displayUsed,
                weeklyAverage:      displayAverage * 7,
                weeklyConsumption:  displayUsed    * 7,
                monthlyAverage:     displayAverage * 30,
                monthlyConsumption: displayUsed    * 30,
              ),

            ],
          ),
        ),
      ),
    );
  }
}