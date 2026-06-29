import 'package:flutter/material.dart';
import '../services/auth_service.dart';

class SecurityScreen extends StatefulWidget {
  const SecurityScreen({super.key});

  @override
  State<SecurityScreen> createState() => _SecurityScreenState();
}

class _SecurityScreenState extends State<SecurityScreen> {
  bool _twoFactor      = false;
  bool _loginAlerts    = false;
  bool _dataEncryption = true;
  int _autoLockMinutes = 1;
  bool _isLoading      = true;
  bool _isVerifyingOtp = false;
  bool _isDisabling    = false;
  bool _obscurePassword = true;

  final _passwordController = TextEditingController();
  final List<int> _autoLockOptions = [1, 5, 10, 15, 30, 60];

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  @override
  void dispose() {
    _passwordController.dispose();
    super.dispose();
  }

  // ── Load current settings from backend ───────────────────
  Future<void> _loadSettings() async {
    setState(() => _isLoading = true);

    final result = await AuthService.getSecuritySettings();

    setState(() => _isLoading = false);

    if (result['success']) {
      setState(() {
        _twoFactor   = result['two_factor_enabled']   ?? false;
        _loginAlerts = result['login_alerts_enabled'] ?? false;
        // treat auto_lock_minutes > 1 as "on" (1 is our "off" sentinel)
        _autoLockMinutes = result['auto_lock_minutes'] ?? 1;
      });
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(result['message']), backgroundColor: Colors.red),
      );
    }
  }

  // ── Handle 2FA toggle ────────────────────────────────────
  Future<void> _onTwoFactorToggle(bool val) async {
    if (val) {
      // Enabling — send OTP first then show OTP dialog
      final result = await AuthService.enable2FA();
      if (result['success']) {
        _showOtpDialog();
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(result['message']), backgroundColor: Colors.red),
        );
      }
    } else {
      // Disabling — ask for password first
      _showDisablePasswordDialog();
    }
  }

  // ── Auto lock picker ─────────────────────────────────────
void _showAutoLockPicker() {
  showModalBottomSheet(
    context: context,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (ctx) => Column(
      mainAxisSize: MainAxisSize.min, // Keep this so it shrinks on tall screens
      children: [
        const Padding(
          padding: EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Text(
            'Auto-Lock After',
            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
          ),
        ),
        // Flexible allows the list to take only what it needs, but scroll if it hits the max height limit
        Flexible(
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: _autoLockOptions.map((minutes) => ListTile(
                leading: const Icon(Icons.timer_outlined, color: Color(0xFF0A1B6F)),
                title: Text(
                  minutes == 1 ? 'Off' : '$minutes minutes',
                  style: const TextStyle(fontSize: 14),
                ),
                trailing: _autoLockMinutes == minutes
                    ? const Icon(Icons.check, color: Color(0xFF0A1B6F))
                    : null,
                onTap: () async {
                  Navigator.pop(ctx);
                  final old = _autoLockMinutes;
                  setState(() => _autoLockMinutes = minutes);

                  final result = await AuthService.setAutoLock(minutes);

                  if (!result['success']) {
                    setState(() => _autoLockMinutes = old);
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(result['message']),
                          backgroundColor: Colors.red,
                        ),
                      );
                    }
                  } else {
                    if (mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            minutes == 1
                                ? 'Auto lock disabled.'
                                : 'Auto lock set to $minutes minutes.',
                          ),
                          backgroundColor: const Color(0xFF0A1B6F),
                        ),
                      );
                    }
                  }
                },
              )).toList(), // Remember to convert map to a list
            ),
          ),
        ),
        const SizedBox(height: 12),
      ],
    ),
  );
}

  // ── Handle login alerts toggle ───────────────────────────
  Future<void> _onLoginAlertsToggle(bool val) async {
    setState(() => _loginAlerts = val);

    final result = await AuthService.toggleLoginAlerts(val);

    if (!result['success']) {
      setState(() => _loginAlerts = !val); // revert on failure
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(result['message']), backgroundColor: Colors.red),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(result['message']), backgroundColor: const Color(0xFF0A1B6F)),
      );
    }
  }

  // ── OTP dialog for enabling 2FA ──────────────────────────
  void _showOtpDialog() {
    final List<TextEditingController> otpControllers =
        List.generate(6, (_) => TextEditingController());
    final List<FocusNode> focusNodes =
        List.generate(6, (_) => FocusNode());

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) {
          return AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            contentPadding: EdgeInsets.zero,
            // Wrapped in SingleChildScrollView so the dialog scrolls
            // instead of overflowing when vertical space is tight
            // (small screens, or the keyboard pushing things up).
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [

                  // ── Header ──────────────────────────────────
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(vertical: 20),
                    decoration: const BoxDecoration(
                      color: Color(0xFF0A1B6F),
                      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
                    ),
                    child: const Column(
                      children: [
                        Icon(Icons.lock, color: Colors.white, size: 30),
                        SizedBox(height: 8),
                        Text(
                          'Enter OTP',
                          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  ),

                  // ── Body ────────────────────────────────────
                  Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      children: [

                        const Text(
                          'Enter the 6-digit code sent to your email.',
                          textAlign: TextAlign.center,
                        ),

                        const SizedBox(height: 20),

                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: List.generate(6, (i) {
                            return SizedBox(
                              width: 40,
                              child: TextField(
                                controller: otpControllers[i],
                                focusNode: focusNodes[i],
                                keyboardType: TextInputType.number,
                                textAlign: TextAlign.center,
                                maxLength: 1,
                                decoration: const InputDecoration(counterText: ''),
                                onChanged: (val) {
                                  if (val.isNotEmpty && i < 5) {
                                    FocusScope.of(ctx).requestFocus(focusNodes[i + 1]);
                                  } else if (val.isEmpty && i > 0) {
                                    FocusScope.of(ctx).requestFocus(focusNodes[i - 1]);
                                  }
                                },
                              ),
                            );
                          }),
                        ),

                        const SizedBox(height: 8),

                        // ── Resend OTP ────────────────────────
                        Align(
                          alignment: Alignment.centerRight,
                          child: TextButton(
                            onPressed: () async {
                              final result = await AuthService.enable2FA();
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text(result['message']),
                                  backgroundColor: result['success']
                                      ? const Color(0xFF0A1B6F)
                                      : Colors.red,
                                ),
                              );
                            },
                            child: const Text(
                              'Resend OTP',
                              style: TextStyle(color: Color(0xFF0A1B6F), fontSize: 12),
                            ),
                          ),
                        ),

                        const SizedBox(height: 8),

                        // ── Verify button ─────────────────────
                        ElevatedButton(
                          onPressed: _isVerifyingOtp
                              ? null
                              : () async {
                                  final otp = otpControllers.map((c) => c.text).join();

                                  if (otp.length < 6) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text('Enter full OTP'),
                                        backgroundColor: Colors.red,
                                      ),
                                    );
                                    return;
                                  }

                                  setDialogState(() => _isVerifyingOtp = true);

                                  final result = await AuthService.verifyEnable2FA(otp);

                                  setDialogState(() => _isVerifyingOtp = false);

                                  if (result['success']) {
                                    setState(() => _twoFactor = true);
                                    Navigator.pop(ctx);
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text('2FA Enabled Successfully'),
                                        backgroundColor: Color(0xFF0A1B6F),
                                      ),
                                    );
                                  } else {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                        content: Text(result['message']),
                                        backgroundColor: Colors.red,
                                      ),
                                    );
                                  }
                                },
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF0A1B6F),
                          ),
                          child: _isVerifyingOtp
                              ? const SizedBox(
                                  height: 18,
                                  width: 18,
                                  child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                                )
                              : const Text('Verify', style: TextStyle(color: Colors.white)),
                        ),

                        TextButton(
                          onPressed: () {
                            Navigator.pop(ctx);
                            setState(() => _twoFactor = false); // revert toggle
                          },
                          child: const Text('Cancel'),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  // ── Password dialog for disabling 2FA ────────────────────
  void _showDisablePasswordDialog() {
    _passwordController.clear();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) {
          return AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            contentPadding: EdgeInsets.zero,
            backgroundColor: Colors.white,
            // Wrapped in SingleChildScrollView so the dialog scrolls
            // instead of overflowing when vertical space is tight.
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [

                  // ── Header ──────────────────────────────────
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(vertical: 20),
                    decoration: const BoxDecoration(
                      color: Color(0xFF0A1B6F),
                      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
                    ),
                    child: const Column(
                      children: [
                        Icon(Icons.lock_open_outlined, color: Colors.white, size: 30),
                        SizedBox(height: 8),
                        Text(
                          'Disable 2FA',
                          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  ),

                  // ── Body ────────────────────────────────────
                  Padding(
                    padding: const EdgeInsets.all(20),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [

                        const Text(
                          'Enter your password to disable Two-Factor Authentication.',
                          textAlign: TextAlign.center,
                          style: TextStyle(fontSize: 13, color: Colors.black87),
                        ),

                        const SizedBox(height: 16),

                        TextField(
                          controller: _passwordController,
                          obscureText: _obscurePassword,
                          style: const TextStyle(color: Colors.black87),
                          decoration: InputDecoration(
                            hintText: 'Enter your password',
                            hintStyle: TextStyle(color: Colors.grey[400], fontSize: 13),
                            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                            filled: true,
                            fillColor: Colors.white,
                            suffixIcon: IconButton(
                              icon: Icon(
                                _obscurePassword ? Icons.visibility_off : Icons.visibility,
                                size: 18,
                                color: Colors.grey,
                              ),
                              onPressed: () =>
                                  setDialogState(() => _obscurePassword = !_obscurePassword),
                            ),
                          ),
                        ),

                        const SizedBox(height: 20),

                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton(
                            onPressed: _isDisabling
                                ? null
                                : () async {
                                    if (_passwordController.text.isEmpty) {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        const SnackBar(
                                          content: Text('Please enter your password.'),
                                          backgroundColor: Colors.red,
                                        ),
                                      );
                                      return;
                                    }

                                    setDialogState(() => _isDisabling = true);

                                    final result = await AuthService.disable2FA(
                                      password: _passwordController.text,
                                    );

                                    setDialogState(() => _isDisabling = false);

                                    if (result['success'] == true) {
                                      setState(() => _twoFactor = false);
                                      Navigator.pop(ctx);
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        const SnackBar(
                                          content: Text('Two-Factor Authentication disabled.'),
                                          backgroundColor: Color(0xFF0A1B6F),
                                        ),
                                      );
                                    } else if (result['otp_required'] == true) {
                                      // Google-only account — password field doesn't apply, show OTP dialog
                                      Navigator.pop(ctx);
                                      _showDisableOtpDialog();
                                    } else {
                                      ScaffoldMessenger.of(context).showSnackBar(
                                        SnackBar(
                                          content: Text(result['message']),
                                          backgroundColor: Colors.red,
                                        ),
                                      );
                                    }
                                  },
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.red[700],
                              disabledBackgroundColor: Colors.grey[300],
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                            ),
                            child: _isDisabling
                                ? const SizedBox(
                                    height: 18,
                                    width: 18,
                                    child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                                  )
                                : const Text(
                                    'Disable 2FA',
                                    style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                                  ),
                          ),
                        ),

                        const SizedBox(height: 8),

                        Center(
                          child: TextButton(
                            onPressed: () => Navigator.pop(ctx),
                            child: const Text('Cancel', style: TextStyle(color: Colors.grey)),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  // ── OTP dialog for disabling 2FA (Google-only accounts) ──
void _showDisableOtpDialog() {
  final List<TextEditingController> otpControllers =
      List.generate(6, (_) => TextEditingController());
  final List<FocusNode> focusNodes =
      List.generate(6, (_) => FocusNode());

  showDialog(
    context: context,
    barrierDismissible: false,
    builder: (ctx) => StatefulBuilder(
      builder: (ctx, setDialogState) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          contentPadding: EdgeInsets.zero,
          backgroundColor: Colors.white,
          // Wrapped in SingleChildScrollView so the dialog scrolls
          // instead of overflowing when vertical space is tight.
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [

                // ── Header ────────────────────────────────────
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(vertical: 20),
                  decoration: const BoxDecoration(
                    color: Color(0xFF0A1B6F),
                    borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
                  ),
                  child: const Column(
                    children: [
                      Icon(Icons.lock_open_outlined, color: Colors.white, size: 30),
                      SizedBox(height: 8),
                      Text(
                        'Disable 2FA',
                        style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                ),

                // ── Body ──────────────────────────────────────
                Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    children: [

                      const Text(
                        'A verification code has been sent to your email. Enter it below to disable 2FA.',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 13, color: Colors.black87),
                      ),

                      const SizedBox(height: 20),

                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: List.generate(6, (i) {
                          return SizedBox(
                            width: 40,
                            child: TextField(
                              controller: otpControllers[i],
                              focusNode: focusNodes[i],
                              keyboardType: TextInputType.number,
                              textAlign: TextAlign.center,
                              maxLength: 1,
                              decoration: const InputDecoration(counterText: ''),
                              onChanged: (val) {
                                if (val.isNotEmpty && i < 5) {
                                  FocusScope.of(ctx).requestFocus(focusNodes[i + 1]);
                                } else if (val.isEmpty && i > 0) {
                                  FocusScope.of(ctx).requestFocus(focusNodes[i - 1]);
                                }
                              },
                            ),
                          );
                        }),
                      ),

                      const SizedBox(height: 20),

                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _isDisabling
                              ? null
                              : () async {
                                  final otp = otpControllers.map((c) => c.text).join();

                                  if (otp.length < 6) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text('Enter the full 6-digit code.'),
                                        backgroundColor: Colors.red,
                                      ),
                                    );
                                    return;
                                  }

                                  setDialogState(() => _isDisabling = true);

                                  final result = await AuthService.disable2FA(otp: otp);

                                  setDialogState(() => _isDisabling = false);

                                  if (result['success'] == true) {
                                    setState(() => _twoFactor = false);
                                    Navigator.pop(ctx);
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text('Two-Factor Authentication disabled.'),
                                        backgroundColor: Color(0xFF0A1B6F),
                                      ),
                                    );
                                  } else {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                        content: Text(result['message']),
                                        backgroundColor: Colors.red,
                                      ),
                                    );
                                  }
                                },
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.red[700],
                            disabledBackgroundColor: Colors.grey[300],
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(10)),
                          ),
                          child: _isDisabling
                              ? const SizedBox(
                                  height: 18,
                                  width: 18,
                                  child: CircularProgressIndicator(
                                      color: Colors.white, strokeWidth: 2),
                                )
                              : const Text(
                                  'Confirm Disable',
                                  style: TextStyle(
                                      fontSize: 15,
                                      fontWeight: FontWeight.bold,
                                      color: Colors.white),
                                ),
                        ),
                      ),

                      const SizedBox(height: 8),

                      Center(
                        child: TextButton(
                          onPressed: () {
                            Navigator.pop(ctx);
                            setState(() => _twoFactor = true); // revert toggle
                          },
                          child: const Text('Cancel', style: TextStyle(color: Colors.grey)),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    ),
  );
}



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
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: Color(0xFF0A1B6F)))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [

                  const SizedBox(height: 10),

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

                        // ── 2FA toggle ─────────────────────
                        _buildToggleTile(
                          icon: Icons.verified_user_outlined,
                          title: 'Two-Factor Authentication',
                          subtitle: 'Require OTP on every login',
                          value: _twoFactor,
                          onChanged: _onTwoFactorToggle,
                        ),

                        _buildDivider(),

                        // ── Login alerts toggle ─────────────
                        _buildToggleTile(
                          icon: Icons.notifications_active_outlined,
                          title: 'Login Alerts',
                          subtitle: 'Get notified of new sign-ins',
                          value: _loginAlerts,
                          onChanged: _onLoginAlertsToggle,
                        ),

                        _buildDivider(),

                        // ── Data encryption (local only) ────
                        _buildToggleTile(
                          icon: Icons.lock_outline,
                          title: 'Data Encryption',
                          subtitle: 'Encrypt all stored sensor data',
                          value: _dataEncryption,
                          onChanged: (val) => setState(() => _dataEncryption = val),
                        ),

                        _buildDivider(),

                        // ── Auto lock ──────────────────────
                        _buildTapTile(
                          icon: Icons.timer_outlined,
                          title: 'Auto Lock',
                          subtitle: _autoLockMinutes == 1
                              ? 'Disabled'
                              : 'Lock after $_autoLockMinutes minutes',
                          onTap: _showAutoLockPicker,
                          isLast: true,
                        ),
                      ],
                    ),
                  ),

                  
                ],
              ),
            ),
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
      padding: EdgeInsets.only(left: 16, right: 8, top: 4, bottom: isLast ? 4 : 0),
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
                Text(subtitle, style: const TextStyle(fontSize: 12, color: Colors.grey)),
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

  Widget _buildTapTile({
  required IconData icon,
  required String title,
  required String subtitle,
  required VoidCallback onTap,
  bool isLast = false,
}) {
  final isDark = Theme.of(context).brightness == Brightness.dark;

  return InkWell(
    onTap: onTap,
    borderRadius: BorderRadius.circular(18),
    child: Padding(
      padding: EdgeInsets.only(left: 16, right: 8, top: 4, bottom: isLast ? 4 : 0),
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
          const Icon(Icons.chevron_right, color: Colors.grey, size: 20),
        ],
      ),
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