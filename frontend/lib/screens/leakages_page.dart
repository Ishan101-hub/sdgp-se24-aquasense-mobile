import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../widgets/leakage_card.dart';
import '../widgets/bell_button.dart';

class LeakagesPage extends StatefulWidget {
  final void Function(int tabIndex) onSwitchTab;

  const LeakagesPage({super.key, required this.onSwitchTab});

  @override
  State<LeakagesPage> createState() => _LeakagesPageState();
}

class _LeakagesPageState extends State<LeakagesPage> {

  // ── Change to your FastAPI URL ──
  static const String _baseUrl   = 'http://192.168.1.XX:8000';
  static const String _networkId = 'home_01'; // your network ID

  bool _isLoading           = true;
  String? _error;
  List<PipelineZone> _zones = [];
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _fetchZones();
    // Auto-refresh every 5 seconds (faster for leak detection!) ✅
    _timer = Timer.periodic(
      const Duration(seconds: 5),
      (_) => _fetchZones(),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  // ── Fetch all zones from backend ──
  // GET /mobile/zones?network_id=home_01
  // Backend is source of truth — render ALL devices including offline ✅
  Future<void> _fetchZones() async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/mobile/zones?network_id=$_networkId'),
      ).timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as List<dynamic>;

        if (mounted) {
          setState(() {
            // Do NOT filter — always render what backend sends ✅
            _zones     = data.map((z) => PipelineZone.fromJson(z)).toList();
            _isLoading = false;
            _error     = null;
          });
        }
      } else {
        throw Exception('Server error ${response.statusCode}');
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _error     = 'Failed to load devices.\nCheck your connection.';
        });
      }
    }
  }

  // ── Valve toggle → POST /mobile/valve ──
  Future<void> _handleValveToggle(PipelineZone zone, bool isOpen) async {
    try {
      await http.post(
        Uri.parse('$_baseUrl/mobile/valve'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'device_id': zone.name, // use zone name as device ID
          'open':      isOpen,
        }),
      ).timeout(const Duration(seconds: 5));

      // Refresh immediately after valve change
      await _fetchZones();

    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Failed to control valve. Try again.'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    // Notifications fetched dynamically by BellButton from backend

    return Scaffold(
      backgroundColor: isDark
          ? const Color(0xFF121212)
          : const Color(0xFFEEF4FF),
      body: SafeArea(
        child: Stack(
          children: [

            // ── Loading state ──
            if (_isLoading)
              const Center(
                child: CircularProgressIndicator(color: Color(0xFF1A1A6E)),
              )

            // ── Error state ──
            else if (_error != null)
              Center(
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
                        setState(() { _isLoading = true; _error = null; });
                        _fetchZones();
                      },
                      icon: const Icon(Icons.refresh),
                      label: const Text('Retry'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF1A1A6E),
                        foregroundColor: Colors.white,
                      ),
                    ),
                  ],
                ),
              )

            // ── Empty state ──
            else if (_zones.isEmpty)
              Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.devices_other, size: 60,
                        color: isDark ? Colors.white30 : Colors.grey),
                    const SizedBox(height: 16),
                    Text(
                      'No devices found',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                        color: isDark ? Colors.white54 : Colors.grey,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Add a device to get started',
                      style: TextStyle(
                        fontSize: 13,
                        color: isDark ? Colors.white38 : Colors.grey,
                      ),
                    ),
                  ],
                ),
              )

            // ── Zone cards ──
            else
              SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
                child: Column(
                  children: [

                    // ── Dynamic cards — ALL devices including offline ✅ ──
                    ..._zones.map((zone) => Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: LeakageCard(
                        zone: zone,
                        onValveToggle: (isOpen) =>
                            _handleValveToggle(zone, isOpen),
                      ),
                    )),

                    // Add a Device card always at bottom
                    _AddDeviceCard(isDark: isDark),

                  ],
                ),
              ),

            // ── Bell button ──
            Positioned(
              bottom: 16,
              right: 16,
              child: BellButton(
                onSwitchTab: widget.onSwitchTab,
              ),
            ),

          ],
        ),
      ),
    );
  }
}

// ── Add a Device Card ─────────────────────────────────────────
class _AddDeviceCard extends StatelessWidget {
  final bool isDark;

  const _AddDeviceCard({required this.isDark});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Device setup coming soon!'),
            backgroundColor: Color(0xFF1A1A6E),
            duration: Duration(seconds: 2),
          ),
        );
      },
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 16),
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E1E1E) : const Color(0xFFEEF4FF),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: const Color(0xFF1A1A6E).withValues(alpha: 0.2),
            width: 1.5,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.06),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 40, height: 40,
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                color: Color(0xFF1A1A6E),
              ),
              child: const Icon(Icons.add, color: Colors.white, size: 24),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Add a Device',
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF1A1A6E),
                    ),
                  ),
                  Text(
                    'Tap to connect a new ESP32 pipeline sensor',
                    style: TextStyle(
                      fontSize: 11,
                      color: isDark ? Colors.white54 : const Color(0xFF888888),
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_ios, color: Color(0xFF1A1A6E), size: 16),
          ],
        ),
      ),
    );
  }
}