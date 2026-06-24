import 'package:flutter/material.dart';
import 'home_screen.dart';
import '../services/auth_service.dart';
import 'package:google_sign_in/google_sign_in.dart';

class LoginPage extends StatefulWidget {
  LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _formKey = GlobalKey<FormState>();

  // ── Login controllers ────────────────────────────────────
  final _emailController    = TextEditingController();
  final _passwordController = TextEditingController();

  // ── Forgot Password controllers ──────────────────────────
  final _forgotEmailController           = TextEditingController();
  final _forgotNewPasswordController     = TextEditingController();
  final _forgotConfirmPasswordController = TextEditingController();

  // ── 2FA OTP controllers (login) ──────────────────────────
  final List<TextEditingController> _twoFAOtpControllers =
      List.generate(6, (_) => TextEditingController());
  final List<FocusNode> _twoFAOtpFocusNodes =
      List.generate(6, (_) => FocusNode());

  // ── Reset OTP controllers (forgot password) ───────────────
  final List<TextEditingController> _resetOtpControllers =
      List.generate(6, (_) => TextEditingController());
  final List<FocusNode> _resetOtpFocusNodes =
      List.generate(6, (_) => FocusNode());

  bool _isLoggingIn       = false;
  bool _isSendingReset    = false;
  bool _isVerifying2FA    = false;
  bool _isVerifyingReset  = false;
  bool _obscureNew        = true;
  bool _obscureConfirm    = true;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _forgotEmailController.dispose();
    _forgotNewPasswordController.dispose();
    _forgotConfirmPasswordController.dispose();
    for (final c in _twoFAOtpControllers) c.dispose();
    for (final f in _twoFAOtpFocusNodes) f.dispose();
    for (final c in _resetOtpControllers) c.dispose();
    for (final f in _resetOtpFocusNodes) f.dispose();
    super.dispose();
  }

  // ── Login ────────────────────────────────────────────────
  Future<void> _onLogin() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() => _isLoggingIn = true);

    final result = await AuthService.login(
      email:    _emailController.text.trim(),
      password: _passwordController.text,
    );

    setState(() => _isLoggingIn = false);

    if (result['success']) {
      if (result['two_factor_required'] == true) {
        _show2FAOtpDialog();
      } else {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => const HomeScreen()),
        );
      }
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(result['message']), backgroundColor: Colors.red),
      );
    }
  }

  // ── Google Sign-In ────────────────────────────────────────
final _googleSignIn = GoogleSignIn(
  serverClientId: '987459520382-6sqt8najkbjb3ml06nhllei4bmpk67nr.apps.googleusercontent.com',
);

Future<void> _onGoogleSignIn() async {
  try {
    final googleUser = await _googleSignIn.signIn();
    if (googleUser == null) return; // user cancelled

    final googleAuth = await googleUser.authentication;
    final idToken = googleAuth.idToken;

    if (idToken == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Google sign-in failed. Please try again.'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() => _isLoggingIn = true);

    final result = await AuthService.googleLogin(idToken);

    setState(() => _isLoggingIn = false);

    if (result['success']) {
      if (result['two_factor_required'] == true) {
        _show2FAOtpDialog();
      } else {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => const HomeScreen()),
        );
      }
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(result['message']), backgroundColor: Colors.red),
      );
    }
  } catch (e) {
    setState(() => _isLoggingIn = false);
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Google sign-in error: $e'), backgroundColor: Colors.red),
    );
  }
}

  // ── 2FA OTP dialog shown after login ─────────────────────
  void _show2FAOtpDialog() {
    for (final c in _twoFAOtpControllers) c.clear();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) {
          return AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            contentPadding: EdgeInsets.zero,
            backgroundColor: Colors.white,
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [

                // ── Header ──────────────────────────────────
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(vertical: 22),
                  decoration: const BoxDecoration(
                    color: Color(0xFF0A1B6F),
                    borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
                  ),
                  child: const Column(
                    children: [
                      Icon(Icons.verified_user_outlined, color: Colors.white, size: 36),
                      SizedBox(height: 8),
                      Text(
                        'Two-Factor Authentication',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),

                // ── Body ────────────────────────────────────
                Padding(
                  padding: const EdgeInsets.fromLTRB(24, 20, 24, 8),
                  child: Column(
                    children: [

                      const Text(
                        'A 6-digit OTP has been sent to your email. Enter it below to complete login.',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 13, color: Colors.black87, height: 1.5),
                      ),

                      const SizedBox(height: 20),

                      // ── 6 OTP boxes ──────────────────────
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: List.generate(6, (i) {
                          return SizedBox(
                            width: 42,
                            height: 50,
                            child: TextField(
                              controller: _twoFAOtpControllers[i],
                              focusNode: _twoFAOtpFocusNodes[i],
                              keyboardType: TextInputType.number,
                              textAlign: TextAlign.center,
                              maxLength: 1,
                              style: const TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                                color: Color(0xFF0A1B6F),
                              ),
                              decoration: InputDecoration(
                                counterText: '',
                                contentPadding: EdgeInsets.zero,
                                enabledBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(10),
                                  borderSide: const BorderSide(color: Color(0xFF0A1B6F), width: 1.5),
                                ),
                                focusedBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(10),
                                  borderSide: const BorderSide(color: Color(0xFF0A1B6F), width: 2.5),
                                ),
                                filled: true,
                                fillColor: const Color(0xFFEEF2FF),
                              ),
                              onChanged: (val) {
                                if (val.isNotEmpty && i < 5) {
                                  FocusScope.of(ctx).requestFocus(_twoFAOtpFocusNodes[i + 1]);
                                } else if (val.isEmpty && i > 0) {
                                  FocusScope.of(ctx).requestFocus(_twoFAOtpFocusNodes[i - 1]);
                                }
                              },
                            ),
                          );
                        }),
                      ),

                      const SizedBox(height: 16),

                      // ── Verify & Login button ─────────────
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _isVerifying2FA
                              ? null
                              : () async {
                                  final otp = _twoFAOtpControllers.map((c) => c.text).join();

                                  if (otp.length < 6) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text('Please enter the full 6-digit OTP.'),
                                        backgroundColor: Colors.red,
                                      ),
                                    );
                                    return;
                                  }

                                  setDialogState(() => _isVerifying2FA = true);

                                  final result = await AuthService.verify2FALogin(otp);

                                  setDialogState(() => _isVerifying2FA = false);

                                  if (result['success']) {
                                    Navigator.pop(ctx);
                                    Navigator.pushReplacement(
                                      context,
                                      MaterialPageRoute(builder: (_) => const HomeScreen()),
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
                            disabledBackgroundColor: Colors.grey[300],
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          child: _isVerifying2FA
                              ? const SizedBox(
                                  height: 20,
                                  width: 20,
                                  child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                                )
                              : const Text(
                                  'Verify & Login',
                                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white),
                                ),
                        ),
                      ),

                      const SizedBox(height: 12),

                      TextButton(
                        onPressed: () => Navigator.pop(ctx),
                        child: const Text('Cancel', style: TextStyle(color: Colors.grey, fontSize: 13)),
                      ),

                      const SizedBox(height: 8),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  // ── Step 1: Forgot password dialog ───────────────────────
  void _showForgotPasswordDialog() {
    _forgotEmailController.clear();
    _forgotNewPasswordController.clear();
    _forgotConfirmPasswordController.clear();

    final forgotFormKey = GlobalKey<FormState>();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) {
          return AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            contentPadding: EdgeInsets.zero,
            backgroundColor: Colors.white,
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [

                  // ── Header ────────────────────────────────
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(vertical: 22),
                    decoration: const BoxDecoration(
                      color: Color(0xFF0A1B6F),
                      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
                    ),
                    child: const Column(
                      children: [
                        Icon(Icons.lock_reset, color: Colors.white, size: 36),
                        SizedBox(height: 8),
                        Text(
                          'Reset Password',
                          style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  ),

                  // ── Body ──────────────────────────────────
                  Padding(
                    padding: const EdgeInsets.fromLTRB(24, 20, 24, 8),
                    child: Form(
                      key: forgotFormKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [

                          const Text(
                            'Enter your registered email and a new password. We will send an OTP to verify.',
                            textAlign: TextAlign.center,
                            style: TextStyle(fontSize: 13, color: Colors.black87, height: 1.5),
                          ),

                          const SizedBox(height: 18),

                          const Text('Registered Email',
                              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF0A1B6F))),
                          const SizedBox(height: 6),
                          TextFormField(
                            controller: _forgotEmailController,
                            keyboardType: TextInputType.emailAddress,
                            decoration: _dialogInputDecoration('example@gmail.com'),
                            validator: (v) {
                              if (v == null || v.isEmpty) return 'Please enter your email';
                              if (!RegExp(r'^[^@]+@[^@]+\.[^@]+').hasMatch(v)) return 'Enter a valid email';
                              return null;
                            },
                          ),

                          const SizedBox(height: 14),

                          const Text('New Password',
                              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF0A1B6F))),
                          const SizedBox(height: 6),
                          TextFormField(
                            controller: _forgotNewPasswordController,
                            obscureText: _obscureNew,
                            decoration: _dialogInputDecoration(
                              'Enter new password',
                              suffix: IconButton(
                                icon: Icon(_obscureNew ? Icons.visibility_off : Icons.visibility,
                                    size: 18, color: Colors.grey),
                                onPressed: () => setDialogState(() => _obscureNew = !_obscureNew),
                              ),
                            ),
                            validator: (v) {
                              if (v == null || v.isEmpty) return 'Please enter a new password';
                              if (v.length < 8) return 'Minimum 8 characters';
                              if (!v.contains(RegExp(r'[A-Z]'))) return 'Must contain an uppercase letter';
                              if (!v.contains(RegExp(r'[a-z]'))) return 'Must contain a lowercase letter';
                              if (!v.contains(RegExp(r'[0-9]'))) return 'Must contain a digit';
                              if (!v.contains(RegExp(r'[!@#$%^&*()_+\-=\[\]{}|;,./<>?]')))
                                return 'Must contain a special character e.g. !@#%';
                              return null;
                            },
                          ),

                          const SizedBox(height: 14),

                          const Text('Confirm Password',
                              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF0A1B6F))),
                          const SizedBox(height: 6),
                          TextFormField(
                            controller: _forgotConfirmPasswordController,
                            obscureText: _obscureConfirm,
                            decoration: _dialogInputDecoration(
                              'Re-enter new password',
                              suffix: IconButton(
                                icon: Icon(_obscureConfirm ? Icons.visibility_off : Icons.visibility,
                                    size: 18, color: Colors.grey),
                                onPressed: () => setDialogState(() => _obscureConfirm = !_obscureConfirm),
                              ),
                            ),
                            validator: (v) {
                              if (v == null || v.isEmpty) return 'Please confirm your password';
                              if (v != _forgotNewPasswordController.text) return 'Passwords do not match';
                              return null;
                            },
                          ),

                          const SizedBox(height: 22),

                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton(
                              onPressed: _isSendingReset
                                  ? null
                                  : () async {
                                      if (!(forgotFormKey.currentState?.validate() ?? false)) return;

                                      setDialogState(() => _isSendingReset = true);

                                      final result = await AuthService.forgotPassword(
                                        _forgotEmailController.text.trim(),
                                      );

                                      setDialogState(() => _isSendingReset = false);

                                      if (result['success']) {
                                        Navigator.pop(ctx);
                                        _showResetOtpDialog();
                                      } else {
                                        ScaffoldMessenger.of(context).showSnackBar(
                                          SnackBar(content: Text(result['message']), backgroundColor: Colors.red),
                                        );
                                      }
                                    },
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF0A1B6F),
                                disabledBackgroundColor: Colors.grey[300],
                                padding: const EdgeInsets.symmetric(vertical: 14),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                              ),
                              child: _isSendingReset
                                  ? const SizedBox(
                                      height: 20, width: 20,
                                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                                  : const Text('Send OTP',
                                      style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white)),
                            ),
                          ),

                          const SizedBox(height: 8),

                          Center(
                            child: TextButton(
                              onPressed: () => Navigator.pop(ctx),
                              child: const Text('Cancel', style: TextStyle(color: Colors.grey, fontSize: 13)),
                            ),
                          ),

                          const SizedBox(height: 8),
                        ],
                      ),
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

  // ── Step 2: Reset OTP verification dialog ────────────────
  void _showResetOtpDialog() {
    for (final c in _resetOtpControllers) c.clear();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) {
          return AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
            contentPadding: EdgeInsets.zero,
            backgroundColor: Colors.white,
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [

                // ── Header ──────────────────────────────────
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(vertical: 22),
                  decoration: const BoxDecoration(
                    color: Color(0xFF0A1B6F),
                    borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
                  ),
                  child: const Column(
                    children: [
                      Icon(Icons.mark_email_read_outlined, color: Colors.white, size: 36),
                      SizedBox(height: 8),
                      Text('Verify OTP',
                          style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),

                // ── Body ────────────────────────────────────
                Padding(
                  padding: const EdgeInsets.fromLTRB(24, 20, 24, 8),
                  child: Column(
                    children: [

                      const Text(
                        'A 6-digit OTP has been sent to your email. Enter it below to reset your password.',
                        textAlign: TextAlign.center,
                        style: TextStyle(fontSize: 13, color: Colors.black87, height: 1.5),
                      ),

                      const SizedBox(height: 20),

                      // ── 6 OTP boxes ──────────────────────
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: List.generate(6, (i) {
                          return SizedBox(
                            width: 42,
                            height: 50,
                            child: TextField(
                              controller: _resetOtpControllers[i],
                              focusNode: _resetOtpFocusNodes[i],
                              keyboardType: TextInputType.number,
                              textAlign: TextAlign.center,
                              maxLength: 1,
                              style: const TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                                color: Color(0xFF0A1B6F),
                              ),
                              decoration: InputDecoration(
                                counterText: '',
                                contentPadding: EdgeInsets.zero,
                                enabledBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(10),
                                  borderSide: const BorderSide(color: Color(0xFF0A1B6F), width: 1.5),
                                ),
                                focusedBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(10),
                                  borderSide: const BorderSide(color: Color(0xFF0A1B6F), width: 2.5),
                                ),
                                filled: true,
                                fillColor: const Color(0xFFEEF2FF),
                              ),
                              onChanged: (val) {
                                if (val.isNotEmpty && i < 5) {
                                  FocusScope.of(ctx).requestFocus(_resetOtpFocusNodes[i + 1]);
                                } else if (val.isEmpty && i > 0) {
                                  FocusScope.of(ctx).requestFocus(_resetOtpFocusNodes[i - 1]);
                                }
                              },
                            ),
                          );
                        }),
                      ),

                      const SizedBox(height: 8),

                      // ── Resend ────────────────────────────
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton(
                          onPressed: () async {
                            final result = await AuthService.forgotPassword(
                              _forgotEmailController.text.trim(),
                            );
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(result['message']),
                                backgroundColor: result['success'] ? const Color(0xFF0A1B6F) : Colors.red,
                              ),
                            );
                          },
                          child: const Text('Resend OTP',
                              style: TextStyle(color: Color(0xFF0A1B6F), fontWeight: FontWeight.w600, fontSize: 12)),
                        ),
                      ),

                      const SizedBox(height: 8),

                      // ── Verify & Reset button ─────────────
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _isVerifyingReset
                              ? null
                              : () async {
                                  final otp = _resetOtpControllers.map((c) => c.text).join();

                                  if (otp.length < 6) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text('Please enter the full 6-digit OTP.'),
                                        backgroundColor: Colors.red,
                                      ),
                                    );
                                    return;
                                  }

                                  setDialogState(() => _isVerifyingReset = true);

                                  final result = await AuthService.resetPassword(
                                    email: _forgotEmailController.text.trim(),
                                    otp: otp,
                                    newPassword: _forgotNewPasswordController.text,
                                  );

                                  setDialogState(() => _isVerifyingReset = false);

                                  if (result['success']) {
                                    Navigator.pop(ctx);
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text('Password reset successfully! Please log in.'),
                                        backgroundColor: Color(0xFF0A1B6F),
                                      ),
                                    );
                                  } else {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(content: Text(result['message']), backgroundColor: Colors.red),
                                    );
                                  }
                                },
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF0A1B6F),
                            disabledBackgroundColor: Colors.grey[300],
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          child: _isVerifyingReset
                              ? const SizedBox(
                                  height: 20, width: 20,
                                  child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                              : const Text('Verify & Reset Password',
                                  style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Colors.white)),
                        ),
                      ),

                      const SizedBox(height: 12),

                      TextButton(
                        onPressed: () => Navigator.pop(ctx),
                        child: const Text('Cancel', style: TextStyle(color: Colors.grey, fontSize: 13)),
                      ),

                      const SizedBox(height: 8),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  // ── Input decoration helper ───────────────────────────────
  InputDecoration _dialogInputDecoration(String hint, {Widget? suffix}) {
    return InputDecoration(
      hintText: hint,
      hintStyle: TextStyle(color: Colors.grey[400], fontSize: 13),
      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: Colors.grey[300]!)),
      enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: Colors.grey[300]!)),
      focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: const BorderSide(color: Color(0xFF0A1B6F), width: 1.5)),
      filled: true,
      fillColor: Colors.white,
      suffixIcon: suffix,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          Container(
            decoration: const BoxDecoration(
              image: DecorationImage(
                image: AssetImage('assets/icons/water_background.jpg'),
                fit: BoxFit.cover,
              ),
            ),
          ),
          Container(color: Colors.white.withOpacity(0.15)),
          SafeArea(
            child: SingleChildScrollView(
              child: Column(
                children: [
                  const SizedBox(height: 40),
                  Transform.scale(
                    scale: 1.8,
                    child: Image.asset('assets/icons/logo.png', height: 120, fit: BoxFit.contain),
                  ),
                  const SizedBox(height: 40),
                  Container(
                    margin: const EdgeInsets.symmetric(horizontal: 24),
                    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.75),
                      borderRadius: BorderRadius.circular(20),
                      boxShadow: [
                        BoxShadow(color: Colors.black.withOpacity(0.15), blurRadius: 20, offset: const Offset(0, 8)),
                      ],
                    ),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [

                          const Center(
                            child: Text('Login',
                                style: TextStyle(fontSize: 30, fontWeight: FontWeight.bold, color: Color(0xFF1A3A5C))),
                          ),
                          const SizedBox(height: 24),

                          // ── Email ──────────────────────────
                          const Text('Email/Phone :',
                              style: TextStyle(fontSize: 13, color: Color(0xFF1A3A5C), fontWeight: FontWeight.w500)),
                          const SizedBox(height: 6),
                          TextFormField(
                            controller: _emailController,
                            style: const TextStyle(color: Colors.black),
                            decoration: InputDecoration(
                              hintText: 'example@gmail.com',
                              hintStyle: TextStyle(color: Colors.grey[400], fontSize: 13),
                              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                              border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(8),
                                  borderSide: BorderSide(color: Colors.grey[300]!)),
                              enabledBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(8),
                                  borderSide: BorderSide(color: Colors.grey[300]!)),
                              filled: true,
                              fillColor: Colors.white,
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) return 'Please enter your email';
                              if (!RegExp(r'^[^@]+@[^@]+\.[^@]+').hasMatch(value)) return 'Please enter a valid email';
                              return null;
                            },
                          ),
                          const SizedBox(height: 14),

                          // ── Password ───────────────────────
                          const Text('Password',
                              style: TextStyle(fontSize: 13, color: Color(0xFF1A3A5C), fontWeight: FontWeight.w500)),
                          const SizedBox(height: 6),
                          TextFormField(
                            controller: _passwordController,
                            obscureText: true,
                            style: const TextStyle(color: Colors.black),
                            decoration: InputDecoration(
                              hintText: 'Password',
                              hintStyle: TextStyle(color: Colors.grey[400], fontSize: 13),
                              contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                              border: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(8),
                                  borderSide: BorderSide(color: Colors.grey[300]!)),
                              enabledBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(8),
                                  borderSide: BorderSide(color: Colors.grey[300]!)),
                              filled: true,
                              fillColor: Colors.white,
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) return 'Please enter your password';
                              if (value.length < 8) return 'Password must be at least 8 characters';
                              return null;
                            },
                          ),
                          const SizedBox(height: 6),

                          // ── Forgot Password ────────────────
                          Center(
                            child: TextButton(
                              onPressed: _showForgotPasswordDialog,
                              style: TextButton.styleFrom(
                                padding: EdgeInsets.zero,
                                minimumSize: Size.zero,
                                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                              ),
                              child: const Text('Forgot Password?',
                                  style: TextStyle(color: Color(0xFF1A3A5C), fontSize: 12, fontWeight: FontWeight.w500)),
                            ),
                          ),
                          const SizedBox(height: 16),

                          // ── Login button ───────────────────
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton(
                              onPressed: _isLoggingIn ? null : _onLogin,
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF1A3A5C),
                                disabledBackgroundColor: Colors.grey[300],
                                padding: const EdgeInsets.symmetric(vertical: 14),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                elevation: 2,
                              ),
                              child: _isLoggingIn
                                  ? const SizedBox(
                                      height: 20, width: 20,
                                      child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                                  : const Text('Log In',
                                      style: TextStyle(fontSize: 16, color: Colors.white, fontWeight: FontWeight.w600)),
                            ),
                          ),
                          const SizedBox(height: 16),

                          // ── Or continue with ───────────────
                          Center(
                            child: Text('or continue with',
                                style: TextStyle(color: Colors.grey[600], fontSize: 13)),
                          ),
                          const SizedBox(height: 12),
                          Center(
                            child: InkWell(
                              onTap: _isLoggingIn ? null : _onGoogleSignIn,
                              borderRadius: BorderRadius.circular(50),
                              child: Container(
                                padding: const EdgeInsets.all(10),
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  border: Border.all(color: Colors.grey[300]!),
                                  color: Colors.white,
                                ),
                                child: Image.asset('assets/icons/google_logo.png', height: 28, width: 28),
                              ),
                            ),
                          ),
                          const SizedBox(height: 16),

                          // ── Register link ──────────────────
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text("Don't have an account?",
                                  style: TextStyle(color: Colors.grey[700], fontSize: 13)),
                              TextButton(
                                onPressed: () => Navigator.pushNamed(context, '/register'),
                                style: TextButton.styleFrom(
                                  padding: const EdgeInsets.only(left: 4),
                                  minimumSize: Size.zero,
                                  tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                ),
                                child: const Text('Register',
                                    style: TextStyle(
                                        color: Color(0xFF1A3A5C), fontWeight: FontWeight.bold, fontSize: 13)),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 40),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}