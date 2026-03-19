import 'package:flutter/material.dart';
import '../services/api_service.dart';

class TermsScreen extends StatefulWidget {
  const TermsScreen({super.key});

  @override
  State<TermsScreen> createState() => _TermsScreenState();
}

class _TermsScreenState extends State<TermsScreen> {
  // Only one checkbox needed
  bool _acceptTerms = false;

  // Loading states
  bool _isLoading = false;
  bool _isPageLoading = true;

  // Error message from backend
  String _errorMessage = "";

  // Button is enabled only when terms checkbox is checked
  bool get _canProceed => _acceptTerms;


  @override
  void initState() {
    super.initState();
    // Load saved checkbox state when page opens
    _loadTermsStatus();
  }


  // ─────────────────────────────────────────────
  // LOAD TERMS STATUS
  // Called when page opens
  // Gets current checkbox state from backend
  // ─────────────────────────────────────────────
  Future<void> _loadTermsStatus() async {
    setState(() => _isPageLoading = true);

    final result = await ApiService.getTermsStatus();

    setState(() => _isPageLoading = false);

    if (result["success"]) {
      final data = result["data"];
      setState(() {
        _acceptTerms = data["terms_of_service"] ?? false;
      });
    }
  }


  // ─────────────────────────────────────────────
  // SAVE TERMS
  // Called when user clicks Confirm and Save
  // Sends checkbox state to backend
  // ─────────────────────────────────────────────
  Future<void> _saveTerms() async {
    setState(() {
      _errorMessage = "";
      _isLoading = true;
    });

    final result = await ApiService.saveTerms(
      termsOfService: _acceptTerms,
    );

    setState(() => _isLoading = false);

    if (!mounted) return;

    if (result["success"]) {
      // Show success message
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Agreements saved successfully!'),
          backgroundColor: Color(0xFF0A1B6F),
        ),
      );

      // Navigate to home screen after saving
      Navigator.pushNamedAndRemoveUntil(
        context,
        "/home",
        (route) => false,
      );
    } else {
      // Show error from backend
      setState(() => _errorMessage = result["message"]);
    }
  }


  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    // Show loading spinner while page is loading saved state
    if (_isPageLoading) {
      return Scaffold(
        backgroundColor:
            isDark ? const Color(0xFF121212) : Colors.grey[100],
        appBar: AppBar(
          backgroundColor: const Color(0xFF0A1B6F),
          title: const Text('Terms & Conditions',
              style: TextStyle(color: Colors.white)),
          iconTheme: const IconThemeData(color: Colors.white),
        ),
        body: const Center(
          child: CircularProgressIndicator(
            color: Color(0xFF0A1B6F),
          ),
        ),
      );
    }

    return Scaffold(
      backgroundColor:
          isDark ? const Color(0xFF121212) : Colors.grey[100],
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

            // ── Terms Text Card ──
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
                      color: isDark
                          ? Colors.white
                          : const Color(0xFF0A1B6F),
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

            // ── Your Agreements Title ──
            Text(
              'Your Agreements',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: isDark ? Colors.white : const Color(0xFF0A1B6F),
              ),
            ),
            const SizedBox(height: 12),

            // ── Checkbox Card ──
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
                  // ── Single Required Checkbox ──
                  _buildCheckTile(
                    title: 'I accept the Terms of Service',
                    subtitle: 'Required to use AquaSense',
                    value: _acceptTerms,
                    isRequired: true,
                    isLast: true,
                    onChanged: (val) =>
                        setState(() => _acceptTerms = val!),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),

            // ── Error Message from Backend ──
            if (_errorMessage.isNotEmpty)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                margin: const EdgeInsets.only(bottom: 8),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline,
                        color: Colors.red, size: 18),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _errorMessage,
                        style: const TextStyle(
                            color: Colors.red, fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),

            // ── Required Fields Notice ──
            if (!_canProceed)
              const Padding(
                padding: EdgeInsets.only(left: 4),
                child: Text(
                  '* Please accept the Terms of Service to continue.',
                  style: TextStyle(color: Colors.red, fontSize: 12),
                ),
              ),
            const SizedBox(height: 24),

            // ── Confirm and Save Button ──
            // Disabled until checkbox is checked
            // Shows loading spinner while saving to backend
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _canProceed && !_isLoading
                    ? _saveTerms
                    : null,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF0A1B6F),
                  disabledBackgroundColor: Colors.grey[300],
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
                child: _isLoading
                    ? const SizedBox(
                        width: 20,
                        height: 20,
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
                          color:
                              _canProceed ? Colors.white : Colors.grey,
                        ),
                      ),
              ),
            ),
            const SizedBox(height: 20),
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
      padding: EdgeInsets.only(
          left: 16, right: 8, top: 4, bottom: isLast ? 4 : 0),
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
                          color:
                              isDark ? Colors.white : Colors.black),
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
                  style: const TextStyle(
                      fontSize: 11.5, color: Colors.grey),
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