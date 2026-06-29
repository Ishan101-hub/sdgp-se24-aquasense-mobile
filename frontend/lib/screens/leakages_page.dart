// lib/screens/leakages_page.dart
// AquaSense — Leakages tab.
// Fetches live zone data from GET /mobile/leakages via ApiService.
// Sends valve commands via POST /mobile/valve (zone_id + action).
// Refreshes every 5 seconds for fast leak detection.
//
// NOTE: BellButton removed. Notifications are handled by the shell-level
// FAB in home_screen.dart so they stay visible on every tab.

import 'dart:async';
import 'package:flutter/material.dart';

import '../models/mobile_models.dart';
import '../services/api_service.dart';
import '../widgets/leakage_card.dart';
import '../screens/device_pairing_intro_screen.dart';

class LeakagesPage extends StatefulWidget {
  final void Function(int tabIndex) onSwitchTab;

  const LeakagesPage({super.key, required this.onSwitchTab});

  @override
  State<LeakagesPage> createState() => _LeakagesPageState();
}

class _LeakagesPageState extends State<LeakagesPage> {
  final _api = ApiService();

  bool _isLoading          = true;
  String? _error;
  List<LeakageZone> _zones = [];
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _fetchZones();
    // Auto-refresh every 5 seconds — fast enough for leak detection
    _timer = Timer.periodic(const Duration(seconds: 5), (_) => _fetchZones());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  // ── Fetch all zones from GET /mobile/leakages ──────────────────────────
  Future<void> _fetchZones() async {
    try {
      final zones = await _api.fetchLeakages();
      if (mounted) {
        setState(() {
          _zones     = zones;
          _isLoading = false;
          _error     = null;
        });
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

  // ── Valve toggle → POST /mobile/valve ─────────────────────────────────
  Future<void> _handleValveToggle(LeakageZone zone, bool isOpen) async {
    try {
      await _api.sendValveCommand(
        ValveCommand(
          zoneId:   zone.zoneId,
          action:   isOpen ? 'open' : 'close',
          override: false,
        ),
      );
      await _fetchZones();
    } on Exception catch (e) {
      if (!mounted) return;
      final msg = e.toString().replaceFirst('Exception: ', '');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content:         Text(msg),
          backgroundColor: Colors.red,
          duration:        const Duration(seconds: 4),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor:
          isDark ? const Color(0xFF121212) : const Color(0xFFEEF4FF),
      body: SafeArea(child: _buildBody(isDark)),
    );
  }

  Widget _buildBody(bool isDark) {
    // ── Loading ──────────────────────────────────────────────────────────
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(color: Color(0xFF1A1A6E)),
      );
    }

    // ── Error ────────────────────────────────────────────────────────────
    if (_error != null) {
      return Center(
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
                _fetchZones();
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
      );
    }

    // ── Empty ────────────────────────────────────────────────────────────
    if (_zones.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.devices_other,
                size: 60,
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
      );
    }

    // ── Zone cards ───────────────────────────────────────────────────────
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
      child: Column(
        children: [
          ..._zones.map((zone) => Padding(
            padding: const EdgeInsets.only(bottom: 16),
            child: LeakageCard(
              zone:          zone,
              onValveToggle: (isOpen) => _handleValveToggle(zone, isOpen),
            ),
          )),
          _AddDeviceCard(isDark: isDark),
        ],
      ),
    );
  }
}

// ── Add a Device Card ──────────────────────────────────────────────────────
class _AddDeviceCard extends StatelessWidget {
  final bool isDark;
  const _AddDeviceCard({required this.isDark});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => const DevicePairingIntroScreen(),
        ),
      ),
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
              color:      Colors.black.withValues(alpha: 0.06),
              blurRadius: 12,
              offset:     const Offset(0, 4),
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
                      fontSize:   15,
                      fontWeight: FontWeight.bold,
                      color:      Color(0xFF1A1A6E),
                    ),
                  ),
                  Text(
                    'Tap to connect a new ESP32 pipeline sensor',
                    style: TextStyle(
                      fontSize: 11,
                      color: isDark
                          ? Colors.white54
                          : const Color(0xFF888888),
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_ios,
                color: Color(0xFF1A1A6E), size: 16),
          ],
        ),
      ),
    );
  }
}