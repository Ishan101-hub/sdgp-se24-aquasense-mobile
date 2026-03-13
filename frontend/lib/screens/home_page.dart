import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../widgets/today_card.dart';
import '../widgets/water_status_card.dart';
import '../widgets/daily_consumption_card.dart';
import '../widgets/bell_button.dart';
import '../widgets/usage_chart_card.dart';
import '../widgets/usage_summary_card.dart';

class HomePage extends StatefulWidget {
  final void Function(int tabIndex) onSwitchTab;

  const HomePage({super.key, required this.onSwitchTab});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {

  // ── Change this to your FastAPI server URL ──
  static const String _baseUrl = 'http://192.168.1.XX:8000';

  bool _isLoading = true;
  String? _error;

  // ── Live data from backend ──
  List<WaterZone> _zones = [];
  double _flowRate       = 0.0;

  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _fetchData();
    // Auto-refresh every 10 seconds
    _timer = Timer.periodic(
      const Duration(seconds: 10),
      (_) => _fetchData(),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  // ── Fetch zones from GET /mobile/zones/daily ──
  // Backend now returns ALL zones dynamically:
  // [
  //   {"name": "Bathroom 01", "used": 60.0, "average": 100.0},
  //   {"name": "Bathroom 02", "used": 80.0, "average": 100.0},
  //   {"name": "Kitchen 01",  "used": 80.0, "average": 100.0},
  //   {"name": "Outdoor 01",  "used": 50.0, "average": 80.0},
  // ]
  Future<void> _fetchData() async {
    try {
      final results = await Future.wait([
        http.get(Uri.parse('$_baseUrl/mobile/zones/daily')),
        http.get(Uri.parse('$_baseUrl/mobile/flowrate')),
      ]);

      final zonesResponse    = results[0];
      final flowRateResponse = results[1];

      if (zonesResponse.statusCode == 200 &&
          flowRateResponse.statusCode == 200) {

        final zonesData = jsonDecode(zonesResponse.body) as List<dynamic>;
        final flowData  = jsonDecode(flowRateResponse.body);

        if (mounted) {
          setState(() {
            // ── Dynamically build zones list from API ──
            // Works for 1 zone, 10 zones, any number! ✅
            _zones = zonesData.map((z) => WaterZone(
              name:    z['name']    as String,
              used:    (z['used']    as num).toDouble(),
              average: (z['average'] as num).toDouble(),
            )).toList();

            _flowRate  = (flowData['flow_rate'] as num).toDouble();
            _isLoading = false;
            _error     = null;
          });
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _error     = 'Failed to load data. Check connection.';
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    // ── Loading state ──
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(color: Color(0xFF1A1A6E)),
      );
    }

    // ── Error state ──
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.wifi_off, size: 60, color: Colors.grey),
            const SizedBox(height: 16),
            Text(_error!, style: const TextStyle(color: Colors.grey)),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () {
                setState(() { _isLoading = true; _error = null; });
                _fetchData();
              },
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    // ── Auto-calculate totals from dynamic zones ──
    // Works for any number of zones! ✅
    final double totalUsed    = _zones.fold(0, (sum, z) => sum + z.used);
    final double totalAverage = _zones.fold(0, (sum, z) => sum + z.average);
    final double percent      = totalAverage > 0
        ? (totalUsed / totalAverage * 100).clamp(0, 999)
        : 0;

    // ── Auto-generate notifications from live data ──
    final List<AppNotification> notifications = [
      ..._zones
          .where((z) => z.used >= z.average)
          .map((z) => AppNotification(
                title:            'Over Limit: ${z.name}',
                message:          '${z.name} consumption reached '
                                  '${z.used.toStringAsFixed(1)}L, exceeding '
                                  'the daily average of '
                                  '${z.average.toStringAsFixed(1)}L.',
                type:             'consumption',
                time:             'Just now',
                targetTabIndex:   0,
              )),
    ];

    return Scaffold(
      backgroundColor: isDark
          ? const Color(0xFF121212)
          : const Color(0xFFEEF4FF),
      body: SafeArea(
        child: Stack(
          children: [

            SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
              child: Column(
                children: [

                  // ── Today card + Water Status card ──
                  IntrinsicHeight(
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Expanded(
                          child: TodayCard(
                            litresUsed:           totalUsed,
                            dailyAverageLitres:   totalAverage,
                            dailyAveragePercent:  percent,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          // ← Real flow rate from ESP32 sensor ✅
                          child: WaterStatusCard(flowRate: _flowRate),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 16),

                  // ── Daily Consumption card ──
                  // Passes dynamic zones from API
                  // UI automatically shows however many zones backend returns ✅
                  DailyConsumptionCard(zones: _zones),

                  const SizedBox(height: 16),

                  UsageChartCard(todayUsage: totalUsed),

                  const SizedBox(height: 16),

                  UsageSummaryCard(
                    dailyAverage:       totalAverage,
                    dailyConsumption:   totalUsed,
                    weeklyAverage:      totalAverage * 7,
                    weeklyConsumption:  totalUsed * 7,
                    monthlyAverage:     totalAverage * 30,
                    monthlyConsumption: totalUsed * 30,
                  ),

                ],
              ),
            ),

            Positioned(
              bottom: 16,
              right: 16,
              child: BellButton(
                hasNotification: notifications.isNotEmpty,
                notifications:   notifications,
                onSwitchTab:     widget.onSwitchTab,
              ),
            ),

          ],
        ),
      ),
    );
  }
}