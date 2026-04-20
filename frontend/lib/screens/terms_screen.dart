import 'package:flutter/material.dart';
import '../services/auth_service.dart';

class TermsScreen extends StatefulWidget {
  const TermsScreen({super.key});

  @override
  State<TermsScreen> createState() => _TermsScreenState();
}

class _TermsScreenState extends State<TermsScreen> {
  bool _acceptTerms  = false;
  bool _isSaving     = false;

  bool get _canProceed => _acceptTerms;

  // ── Save terms to backend ────────────────────────────────
  Future<void> _onConfirm() async {
    setState(() => _isSaving = true);

    final result = await AuthService.saveTerms();

    setState(() => _isSaving = false);

    if (result['success']) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Agreements saved successfully!'),
          backgroundColor: Color(0xFF0A1B6F),
        ),
      );
      // Navigate to home and clear all previous routes
      Navigator.pushNamedAndRemoveUntil(
        context,
        '/home',
        (route) => false,
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(result['message']),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF121212) : Colors.grey[100],
      appBar: AppBar(
        backgroundColor: const Color(0xFF0A1B6F),
        title: const Text('Terms & Conditions',
            style: TextStyle(color: Colors.white)),
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
                color: isDark ? const Color(0xFF1E1E1E) : Colors.white,
                borderRadius: BorderRadius.circular(16),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.06),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'AquaSense Terms of Service',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                      color: isDark ? Colors.white : const Color(0xFF0A1B6F),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'Welcome to AquaSense. By accessing or using the AquaSense smart water management application, '
                    'you agree to be bound by the following Terms and Conditions. Please read them carefully before proceeding.\n\n'
                    '1. Purpose of Service\n'
                    'AquaSense is an IoT-based smart water management, monitoring, and conservation system designed exclusively '
                    'for residential use in Sri Lankan households. The application enables real-time zone-level water consumption '
                    'monitoring, automated leak detection, remote valve control, and usage analytics. Unauthorized use, reverse '
                    'engineering, redistribution, or commercial resale of the software or its components is strictly prohibited.\n\n'
                    '2. Data Collection & Privacy\n'
                    'AquaSense collects IoT sensor data including water flow rates, pressure readings, zone consumption logs, '
                    'leak detection events, valve status, and personal account information. This data is processed by our FastAPI '
                    'backend, stored securely in MongoDB Atlas cloud, and protected using industry-standard encryption. All data '
                    'is handled in accordance with applicable privacy regulations. We do not sell or share your personal data '
                    'with third parties without your explicit consent.\n\n'
                    '3. Device & Sensor Accuracy\n'
                    'AquaSense uses YF-S201 flow sensors and ESP32 microcontrollers to capture real-time water data. While the '
                    'system is designed for high accuracy, sensor readings may be affected by water pressure fluctuations, pipe '
                    'conditions, Wi-Fi connectivity issues, or hardware faults. AquaSense does not guarantee 100% accuracy of '
                    'sensor data at all times.\n\n'
                    '4. Liability\n'
                    'AquaSense and its developers are not liable for water damage, supply interruptions, or financial loss '
                    'resulting from system errors, sensor malfunctions, connectivity failures, or incorrect automated valve '
                    'actions. In all emergency situations, manual override of valves and physical intervention is always '
                    'recommended.\n\n'
                    '5. Notifications & Alerts\n'
                    'AquaSense uses Firebase Cloud Messaging to deliver real-time push notifications for leak detections, '
                    'device errors, and account security alerts. Notification delivery depends on your device settings and '
                    'network availability. AquaSense is not responsible for missed alerts due to disabled notifications or '
                    'poor connectivity.\n\n'
                    '6. Modifications to Terms\n'
                    'AquaSense reserves the right to update or modify these Terms and Conditions at any time without prior '
                    'notice. Continued use of the application following any changes constitutes your acceptance of the revised '
                    'terms. We encourage users to review these terms periodically.\n\n'
                    '7. Governing Law\n'
                    'These terms are governed by the applicable laws of Sri Lanka, including relevant data protection and '
                    'consumer rights regulations. Any disputes arising from the use of AquaSense shall be subject to the '
                    'jurisdiction of Sri Lankan courts.',
                    style: TextStyle(
                      fontSize: 13,
                      color: isDark ? Colors.white70 : Colors.black87,
                      height: 1.6,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'Your Agreements',
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
                  _buildCheckTile(
                    title: 'I accept the Terms of Service',
                    subtitle: 'Required to use AquaSense',
                    value: _acceptTerms,
                    isRequired: true,
                    onChanged: (val) => setState(() => _acceptTerms = val!),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            if (!_canProceed)
              const Padding(
                padding: EdgeInsets.only(left: 4),
                child: Text(
                  '* Please accept all required agreements to continue.',
                  style: TextStyle(color: Colors.red, fontSize: 12),
                ),
              ),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _canProceed && !_isSaving ? _onConfirm : null,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF0A1B6F),
                  disabledBackgroundColor: Colors.grey[300],
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
                child: _isSaving
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                          color: Colors.white,
                          strokeWidth: 2,
                        ),
                      )
                    : Text(
                        'Confirm & Save',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: _canProceed ? Colors.white : Colors.grey,
                        ),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCheckTile({
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool?> onChanged,
    bool isRequired = false,
    bool isLast = false,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Padding(
      padding:
          EdgeInsets.only(left: 16, right: 8, top: 4, bottom: isLast ? 4 : 0),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 12),
                Row(
                  children: [
                    Text(
                      title,
                      style: TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 13.5,
                          color: isDark ? Colors.white : Colors.black),
                    ),
                    if (isRequired) ...[
                      const SizedBox(width: 4),
                      const Text('*',
                          style: TextStyle(
                              color: Colors.red,
                              fontWeight: FontWeight.bold)),
                    ],
                  ],
                ),
                const SizedBox(height: 3),
                Text(
                  subtitle,
                  style: const TextStyle(fontSize: 11.5, color: Colors.grey),
                ),
                const SizedBox(height: 12),
              ],
            ),
          ),
          Checkbox(
            value: value,
            onChanged: onChanged,
            activeColor: const Color(0xFF0A1B6F),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(4),
            ),
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