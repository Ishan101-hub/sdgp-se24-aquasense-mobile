// lib/screens/device_setup_form_screen.dart
// AquaSense — Step 3: Ping device, collect WiFi creds, send config

import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../services/api_service.dart';
import 'device_connecting_screen.dart';

class DeviceSetupFormScreen extends StatefulWidget {
  const DeviceSetupFormScreen({super.key});

  @override
  State<DeviceSetupFormScreen> createState() => _DeviceSetupFormScreenState();
}

class _DeviceSetupFormScreenState extends State<DeviceSetupFormScreen> {
  static const String _deviceIp = 'http://192.168.4.1';

  final _api    = ApiService();
  final _formKey    = GlobalKey<FormState>();

  final _ssidController     = TextEditingController();
  final _passwordController = TextEditingController();

  bool    _checkingDevice  = true;
  bool    _deviceFound     = false;
  bool    _isSubmitting    = false;
  bool    _obscurePassword = true;
  String? _chipId;
  String? _sensorType;
  String? _errorMessage;

  // Network/zone selection
  List<Map<String, dynamic>> _networks = [];
  List<Map<String, dynamic>> _zones    = [];
  int?    _selectedNetworkId;
  String? _selectedNetworkSlug;
  String? _selectedZoneSlug;
  String? _selectedSensorType;

  @override
  void initState() {
    super.initState();
    _pingDevice();
    _loadNetworks();
  }

  @override
  void dispose() {
    _ssidController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  // ── Ping the ESP32 at 192.168.4.1 ────────────────────────────────────────
  Future<void> _pingDevice() async {
    setState(() {
      _checkingDevice = true;
      _errorMessage   = null;
    });

    try {
      final res = await http
          .get(Uri.parse('$_deviceIp/info'))
          .timeout(const Duration(seconds: 6));

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        setState(() {
          _chipId      = data['chip_id']     as String?;
          _sensorType  = data['sensor_type'] as String?;
          _deviceFound = true;
        });
      } else {
        setState(() => _errorMessage = 'Device responded with an error. Try again.');
      }
    } catch (_) {
      setState(() => _errorMessage =
          'Device not found. Make sure you are connected to the AquaSense-Setup WiFi network.');
    } finally {
      setState(() => _checkingDevice = false);
    }
  }

  // ── Load user's networks from backend ────────────────────────────────────
  Future<void> _loadNetworks() async {
    try {
      print("📡 Fetching networks from API...");
      final networks = await _api.fetchNetworks();
      print("✅ Networks response from API: $networks");
      
      setState(() {
        _networks = List<Map<String, dynamic>>.from(networks);
      });
    } catch (e) {
      print("❌ Error fetching networks: $e");
      setState(() {
        _errorMessage = "Failed to load networks from server: $e";
      });
    }
  }

  // ── Load zones for selected network ──────────────────────────────────────
  Future<void> _loadZones(int networkId) async {
    try {
      print("📡 Fetching zones for Network ID: $networkId...");
      final zones = await _api.fetchZones(networkId);
      print("✅ Zones response from API: $zones");
      
      setState(() {
        _zones            = List<Map<String, dynamic>>.from(zones);
        _selectedZoneSlug = null; 
      });
    } catch (e) {
      print("❌ Error fetching zones: $e");
    }
  }

  // ── Submit: get config from backend → send to ESP32 → register device ───
  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    if (_selectedNetworkSlug == null || _selectedZoneSlug == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content:          Text('Please select a network and zone.'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() => _isSubmitting = true);

    try {
      // Step 1 — Get provisioning config from backend
      final config = await _api.generateProvisioningConfig(
        networkId:  _selectedNetworkSlug!,
        zoneId:     _selectedZoneSlug!,
        sensorType: _selectedSensorType ?? _sensorType ?? 'inlet',
        chipId:     _chipId!,
      );

      // Step 2 — Send config + WiFi creds to the ESP32 over the local AP
      final configPayload = {
        'wifi_ssid':        _ssidController.text.trim(),
        'wifi_password':    _passwordController.text,
        'device_id':        config['device_id'],
        'outlet_device_id': config['outlet_device_id'] ?? '',
        'network_id':       config['network_id'],
        'zone_id':          config['zone_id'],
        'mqtt_broker_host': config['mqtt_broker_host'],
        'mqtt_broker_port': config['mqtt_broker_port'],
        'mqtt_username':    config['mqtt_username'],
        'mqtt_password':    config['mqtt_password'],
      };

      final espRes = await http
          .post(
            Uri.parse('$_deviceIp/configure'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(configPayload),
          )
          .timeout(const Duration(seconds: 8));

      if (espRes.statusCode != 200) {
        throw Exception('Device rejected the config. Try again.');
      }

      // Step 3 — Register the device in your backend
      await _api.registerDevice(
        networkId:  _selectedNetworkId!,
        zoneId:     _selectedZoneSlug!,
        deviceId:   config['device_id'] as String,
        sensorType: _selectedSensorType ?? _sensorType ?? 'inlet',
      );

      if (!mounted) return;

      // Step 4 — Navigate to connecting screen
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (_) => DeviceConnectingScreen(
            deviceId: config['device_id'] as String,
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content:          Text(e.toString().replaceFirst('Exception: ', '')),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      appBar: AppBar(
        title: const Text('Device Setup'),
        backgroundColor: const Color(0xFF1A1A6E),
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [

            // ── Device ping status ───────────────────────────────────────
            _buildDeviceStatus(isDark),

            const SizedBox(height: 24),

            if (_deviceFound) ...[

              Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [

                    // ── Network picker ─────────────────────────────────
                    _label('Network', isDark),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<int>(
                      value: _selectedNetworkId,
                      decoration: _inputDeco('Select your network', isDark),
                      dropdownColor: isDark ? const Color(0xFF1E1E2E) : Colors.white,
                      items: _networks.map((n) {
                        return DropdownMenuItem<int>(
                          value: n['id'] as int,
                          child: Text(n['name'] ?? n['network_id'] ?? 'Unknown Network'),
                        );
                      }).toList(),
                      onChanged: (val) {
                        if (val == null) return;
                        final net = _networks.firstWhere((n) => n['id'] == val);
                        setState(() {
                          _selectedNetworkId   = val;
                          // Fallback handling to ensure slug matches whatever field your API passes
                          _selectedNetworkSlug = (net['network_id'] ?? net['slug'] ?? '') as String;
                          _zones = [];
                          _selectedZoneSlug = null;
                        });
                        _loadZones(val);
                      },
                      validator: (v) => v == null ? 'Select a network' : null,
                    ),

                    const SizedBox(height: 16),

                    // ── Zone picker ────────────────────────────────────
                    _label('Zone', isDark),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String>(
                      decoration: _inputDeco(_selectedNetworkId == null ? 'Select a network first' : 'Select zone', isDark),
                      dropdownColor: isDark ? const Color(0xFF1E1E2E) : Colors.white,
                      value: _selectedZoneSlug,
                      items: _zones.map((z) {
                        return DropdownMenuItem<String>(
                          value: z['zone_id'] as String,
                          child: Text(z['zone_name'] ?? z['zone_id'] ?? 'Unnamed Zone'),
                        );
                      }).toList(),
                      onChanged: _networks.isEmpty ? null : (val) => setState(() => _selectedZoneSlug = val),
                      validator: (v) => v == null ? 'Select a zone' : null,
                    ),

                    const SizedBox(height: 16),

                    // ── Sensor type ────────────────────────────────────
                    _label('Sensor Type', isDark),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String>(
                      decoration: _inputDeco('Select type', isDark),
                      dropdownColor: isDark ? const Color(0xFF1E1E2E) : Colors.white,
                      value: _selectedSensorType ?? _sensorType,
                      items: const [
                        DropdownMenuItem(value: 'inlet',  child: Text('Inlet (with valve)')),
                        DropdownMenuItem(value: 'outlet', child: Text('Outlet (flow only)')),
                      ],
                      onChanged: (val) => setState(() => _selectedSensorType = val),
                      validator: (v) => v == null ? 'Select sensor type' : null,
                    ),

                    const SizedBox(height: 24),

                    // ── WiFi credentials ───────────────────────────────
                    _label('Home WiFi Name (SSID)', isDark),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: _ssidController,
                      decoration: _inputDeco('e.g. Home WiFi', isDark),
                      validator: (v) =>
                          (v == null || v.trim().isEmpty) ? 'Enter your WiFi name' : null,
                    ),

                    const SizedBox(height: 16),

                    _label('WiFi Password', isDark),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: _passwordController,
                      obscureText: _obscurePassword,
                      decoration: _inputDeco(
                        'Enter WiFi password',
                        isDark,
                        suffix: IconButton(
                          icon: Icon(
                            _obscurePassword ? Icons.visibility_off : Icons.visibility,
                            color: Colors.grey,
                            size: 18,
                          ),
                          onPressed: () =>
                              setState(() => _obscurePassword = !_obscurePassword),
                        ),
                      ),
                      validator: (v) =>
                          (v == null || v.isEmpty) ? 'Enter your WiFi password' : null,
                    ),

                    const SizedBox(height: 32),

                    // ── Submit ─────────────────────────────────────────
                    SizedBox(
                      width: double.infinity,
                      height: 52,
                      child: ElevatedButton(
                        onPressed: _isSubmitting ? null : _submit,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF1A1A6E),
                          foregroundColor: Colors.white,
                          disabledBackgroundColor: Colors.grey[300],
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                        child: _isSubmitting
                            ? const SizedBox(
                                height: 22,
                                width: 22,
                                child: CircularProgressIndicator(
                                  color: Colors.white,
                                  strokeWidth: 2,
                                ),
                              )
                            : const Text(
                                'Configure Device',
                                style: TextStyle(
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildDeviceStatus(bool isDark) {
    if (_checkingDevice) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.blue.withOpacity(0.06),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.blue.withOpacity(0.2)),
        ),
        child: const Row(
          children: [
            SizedBox(
              width: 20, height: 20,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            SizedBox(width: 14),
            Text('Looking for device at 192.168.4.1...'),
          ],
        ),
      );
    }

    if (_deviceFound) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.green.withOpacity(0.06),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.green.withOpacity(0.3)),
        ),
        child: Row(
          children: [
            const Icon(Icons.check_circle, color: Colors.green),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Device found!',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: Colors.green,
                    ),
                  ),
                  if (_chipId != null)
                    Text(
                      'Chip ID: $_chipId · Type: ${_sensorType ?? "unknown"}',
                      style: const TextStyle(fontSize: 12, color: Colors.grey),
                    ),
                ],
              ),
            ),
          ],
        ),
      );
    }

    // Error state
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.red.withOpacity(0.06),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.red.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.error_outline, color: Colors.red),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  _errorMessage ?? 'Device not found.',
                  style: const TextStyle(color: Colors.red),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextButton.icon(
            onPressed: _pingDevice,
            icon: const Icon(Icons.refresh, size: 16),
            label: const Text('Try Again'),
          ),
        ],
      ),
    );
  }

  Widget _label(String text, bool isDark) => Text(
    text,
    style: TextStyle(
      fontSize: 13,
      fontWeight: FontWeight.w600,
      color: isDark ? Colors.white70 : Colors.black87,
    ),
  );

  InputDecoration _inputDeco(String hint, bool isDark, {Widget? suffix}) =>
      InputDecoration(
        hintText:        hint,
        hintStyle:       TextStyle(color: isDark ? Colors.grey[500] : Colors.grey),
        filled:          true,
        fillColor:       isDark ? const Color(0xFF1E1E2E) : Colors.white,
        contentPadding:  const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        border:          OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
        enabledBorder:   OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide:   BorderSide(
            color: isDark
                ? Colors.white.withOpacity(0.12)
                : const Color(0xFF1A1A6E).withOpacity(0.1),
          ),
        ),
        focusedBorder:   OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide:   const BorderSide(color: Color(0xFF1A1A6E), width: 1.5),
        ),
        errorBorder:     OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide:   const BorderSide(color: Colors.red),
        ),
        suffixIcon: suffix,
      );
}