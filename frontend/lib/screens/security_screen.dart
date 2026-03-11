import 'package:flutter/material.dart';

class SecurityScreen extends StatefulWidget {
  const SecurityScreen({super.key});

  @override
  State<SecurityScreen> createState() => _SecurityScreenState();
}

class _SecurityScreenState extends State<SecurityScreen> {
  bool _twoFactor = false;
  bool _loginAlerts = false;
  bool _dataEncryption = true;
  bool _autoLock = false;

  @override
  Widget build(BuildContext context) {

    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF121212) : Colors.grey[100],
      appBar: AppBar(
        backgroundColor: const Color(0xFF0A1B6F),
        title: const Text('Security', style: TextStyle(color: Colors.white)),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [

            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: const Color(0xFF0A1B6F).withOpacity(0.07),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: const Color(0xFF0A1B6F).withOpacity(0.15),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [

                  const Row(
                    children: [
                      Icon(Icons.shield, color: Color(0xFF0A1B6F), size: 20),
                      SizedBox(width: 8),
                      Text(
                        'Security Settings',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 15,
                          color: Color(0xFF0A1B6F),
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 14),

                  _buildSecurityPoint(
                    emoji: '🔐',
                    title: 'Account Protection',
                    description:
                        'Your account is secured via Firebase Authentication with email verification. Only you can access your AquaSense dashboard and device controls.',
                    isDark: isDark,
                  ),

                  const SizedBox(height: 12),

                  _buildSecurityPoint(
                    emoji: '💧',
                    title: 'Water Data Encryption',
                    description:
                        'All water usage logs, zone consumption records, leak history, and sensor readings are encrypted and stored securely in MongoDB Atlas cloud.',
                    isDark: isDark,
                  ),

                  const SizedBox(height: 12),

                  _buildSecurityPoint(
                    emoji: '📡',
                    title: 'Secure Device Communication',
                    description:
                        'Data transmitted between your ESP32 sensors and the backend travels over MQTTS — MQTT with TLS encryption — preventing unauthorized interception.',
                    isDark: isDark,
                  ),

                  const SizedBox(height: 12),

                  _buildSecurityPoint(
                    emoji: '🔔',
                    title: 'Real-Time Security Alerts',
                    description:
                        'Receive instant push notifications for suspicious login attempts, leak detections, and unauthorized valve control actions through Firebase Cloud Messaging.',
                    isDark: isDark,
                  ),

                  const SizedBox(height: 12),

                  _buildSecurityPoint(
                    emoji: '🛡️',
                    title: 'Your Controls',
                    description:
                        'Use the settings below to enable additional layers of security tailored to your account and home water system.',
                    isDark: isDark,
                  ),

                ],
              ),
            ),

            const SizedBox(height: 24),

            Text(
              'Security Options',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: isDark ? Colors.white : const Color(0xFF0A1B6F),
              ),
            ),

            const SizedBox(height: 12),

            Container(
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF1E1E1E) : Colors.white,
                borderRadius: BorderRadius.circular(18),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.07),
                    blurRadius: 10,
                    offset: const Offset(0, 3),
                  ),
                ],
              ),
              child: Column(
                children: [
                  _buildToggleTile(
                    icon: Icons.verified_user_outlined,
                    title: 'Two-Factor Authentication',
                    subtitle: 'Require OTP on every login',
                    value: _twoFactor,
                    onChanged: (val) => setState(() => _twoFactor = val),
                  ),

                  _buildDivider(),

                  _buildToggleTile(
                    icon: Icons.notifications_active_outlined,
                    title: 'Login Alerts',
                    subtitle: 'Get notified of new sign-ins',
                    value: _loginAlerts,
                    onChanged: (val) => setState(() => _loginAlerts = val),
                  ),

                  _buildDivider(),

                  _buildToggleTile(
                    icon: Icons.lock_outline,
                    title: 'Data Encryption',
                    subtitle: 'Encrypt all stored sensor data',
                    value: _dataEncryption,
                    onChanged: (val) => setState(() => _dataEncryption = val),
                  ),

                  _buildDivider(),

                  _buildToggleTile(
                    icon: Icons.timer_outlined,
                    title: 'Auto Lock',
                    subtitle: 'Lock app after 5 minutes of inactivity',
                    value: _autoLock,
                    onChanged: (val) => setState(() => _autoLock = val),
                    isLast: true,
                  ),
                ],
              ),
            ),

            const SizedBox(height: 28),

            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {

                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Security settings saved!'),
                      backgroundColor: Color(0xFF0A1B6F),
                    ),
                  );

                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF0A1B6F),
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
                child: const Text(
                  'Save Settings',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
              ),
            ),

          ],
        ),
      ),
    );
  }

  Widget _buildSecurityPoint({
    required String emoji,
    required String title,
    required String description,
    required bool isDark,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(emoji, style: const TextStyle(fontSize: 16)),
        const SizedBox(width: 10),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 13.5,
                  color: Color(0xFF0A1B6F),
                ),
              ),
              const SizedBox(height: 3),
              Text(
                description,
                style: TextStyle(
                  fontSize: 12.5,
                  color: isDark ? Colors.white70 : Colors.black87,
                  height: 1.5,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildToggleTile({
    required IconData icon,
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool> onChanged,
    bool isLast = false,
  }) {

    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Padding(
      padding: EdgeInsets.only(
        left: 16,
        right: 8,
        top: 4,
        bottom: isLast ? 4 : 0,
      ),
      child: Row(
        children: [

          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: const Color(0xFF0A1B6F).withOpacity(0.08),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, color: const Color(0xFF0A1B6F), size: 20),
          ),

          const SizedBox(width: 14),

          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [

                Text(
                  title,
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                    color: isDark ? Colors.white : Colors.black,
                  ),
                ),

                Text(
                  subtitle,
                  style: const TextStyle(fontSize: 12, color: Colors.grey),
                ),

              ],
            ),
          ),

          Switch(
            value: value,
            onChanged: onChanged,
            activeColor: Colors.white,
            activeTrackColor: const Color(0xFF0A1B6F),
            inactiveThumbColor: Colors.white,
            inactiveTrackColor: Colors.grey.withOpacity(0.4),
          ),

        ],
      ),
    );
  }

  Widget _buildDivider() => const Divider(
        color: Colors.grey,
        thickness: 0.4,
        height: 0,
        indent: 16,
        endIndent: 16,
      );
}