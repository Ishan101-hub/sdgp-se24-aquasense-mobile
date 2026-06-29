// lib/screens/device_connecting_screen.dart
// AquaSense — Step 4: Wait for device to come online after reboot

import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';

class DeviceConnectingScreen extends StatefulWidget {
  final String deviceId;

  const DeviceConnectingScreen({super.key, required this.deviceId});

  @override
  State<DeviceConnectingScreen> createState() => _DeviceConnectingScreenState();
}

class _DeviceConnectingScreenState extends State<DeviceConnectingScreen> {
  final _api     = ApiService();
  Timer? _timer;
  int    _attempts = 0;
  bool   _success  = false;
  bool   _timedOut = false;

  static const int _maxAttempts = 20;   // 20 × 3s = 60s timeout

  @override
  void initState() {
    super.initState();
    // Give device 5 seconds to reboot before first poll
    Future.delayed(const Duration(seconds: 5), _startPolling);
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  void _startPolling() {
    _timer = Timer.periodic(const Duration(seconds: 3), (_) async {
      _attempts++;

      if (_attempts > _maxAttempts) {
        _timer?.cancel();
        if (mounted) setState(() => _timedOut = true);
        return;
      }

      try {
        final isOnline = await _api.checkDeviceOnline(widget.deviceId);
        if (isOnline && mounted) {
          _timer?.cancel();
          setState(() => _success = true);
        }
      } catch (_) {
        // Keep polling — device may still be connecting
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        title: const Text('Connecting...'),
        backgroundColor: const Color(0xFF1A1A6E),
        foregroundColor: Colors.white,
        elevation: 0,
        automaticallyImplyLeading: false,
      ),
      body: Padding(
        padding: const EdgeInsets.all(32),
        child: Center(
          child: _success
              ? _buildSuccess()
              : _timedOut
                  ? _buildTimeout()
                  : _buildWaiting(),
        ),
      ),
    );
  }

  Widget _buildWaiting() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        const SizedBox(
          width: 80, height: 80,
          child: CircularProgressIndicator(
            color: Color(0xFF1A1A6E),
            strokeWidth: 4,
          ),
        ),
        const SizedBox(height: 32),
        const Text(
          'Device is connecting...',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 12),
        const Text(
          'The device is rebooting and joining your home WiFi. '
          'This usually takes 10–20 seconds.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.grey, height: 1.6),
        ),
        const SizedBox(height: 24),
        Text(
          'Checking... (${_attempts * 3}s)',
          style: const TextStyle(color: Colors.grey, fontSize: 12),
        ),
      ],
    );
  }

  Widget _buildSuccess() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 90, height: 90,
          decoration: BoxDecoration(
            color: Colors.green.withOpacity(0.1),
            shape: BoxShape.circle,
          ),
          child: const Icon(
            Icons.check_circle,
            color: Colors.green,
            size: 52,
          ),
        ),
        const SizedBox(height: 24),
        const Text(
          'Device Online!',
          style: TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.bold,
            color: Colors.green,
          ),
        ),
        const SizedBox(height: 12),
        Text(
          '${widget.deviceId} is connected and sending data.',
          textAlign: TextAlign.center,
          style: const TextStyle(color: Colors.grey, height: 1.6),
        ),
        const SizedBox(height: 32),
        SizedBox(
          width: double.infinity,
          height: 52,
          child: ElevatedButton(
            onPressed: () {
              // Pop back to leakages screen — new device will appear in the list
              Navigator.of(context).popUntil((route) => route.isFirst);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF1A1A6E),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: const Text(
              'Done',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildTimeout() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 90, height: 90,
          decoration: BoxDecoration(
            color: Colors.orange.withOpacity(0.1),
            shape: BoxShape.circle,
          ),
          child: const Icon(
            Icons.wifi_off,
            color: Colors.orange,
            size: 52,
          ),
        ),
        const SizedBox(height: 24),
        const Text(
          'Taking longer than expected',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 12),
        const Text(
          'The device may still be connecting. '
          'Check the Leakages screen in a few moments to see if it appears.',
          textAlign: TextAlign.center,
          style: TextStyle(color: Colors.grey, height: 1.6),
        ),
        const SizedBox(height: 32),
        SizedBox(
          width: double.infinity,
          height: 52,
          child: ElevatedButton(
            onPressed: () =>
                Navigator.of(context).popUntil((route) => route.isFirst),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF1A1A6E),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: const Text(
              'Go to Leakages',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
          ),
        ),
      ],
    );
  }
}