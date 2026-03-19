import 'package:flutter/material.dart';
import '../services/api_service.dart';

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});

  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _formKey = GlobalKey<FormState>();

  // ── Login controllers ──────────────────────────────────
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  // ── Forgot Password controllers ────────────────────────
  final _forgotEmailController = TextEditingController();
  final _forgotNewPasswordController = TextEditingController();
  final _forgotConfirmPasswordController = TextEditingController();

  // ── OTP controllers ────────────────────────────────────
  final List<TextEditingController> _otpControllers =
      List.generate(6, (_) => TextEditingController());
  final List<FocusNode> _otpFocusNodes =
      List.generate(6, (_) => FocusNode());

  // ── Login state ────────────────────────────────────────
  bool _isLoading = false;
  bool _passwordVisible = false;
  String _errorMessage = "";

  // ── Forgot password state ──────────────────────────────
  bool _isSendingReset = false;
  bool _isVerifyingOtp = false;
  bool _isResendingOtp = false;
  bool _obscureNew = true;
  bool _obscureConfirm = true;


  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _forgotEmailController.dispose();
    _forgotNewPasswordController.dispose();
    _forgotConfirmPasswordController.dispose();
    for (final c in _otpControllers) c.dispose();
    for (final f in _otpFocusNodes) f.dispose();
    super.dispose();
  }


  // ─────────────────────────────────────────────
  // LOGIN FUNCTION
  // Calls POST /auth/login on the backend
  // ─────────────────────────────────────────────
  Future<void> _login() async {
    setState(() => _errorMessage = "");

    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() => _isLoading = true);

    final result = await ApiService.login(
      email: _emailController.text.trim(),
      password: _passwordController.text,
    );

    setState(() => _isLoading = false);

    if (!mounted) return;

    if (result["success"]) {
      if (result["two_factor_required"] == true) {
        Navigator.pushNamed(context, "/2fa-verify");
        return;
      }

      // Check terms after login
      final termsResult = await ApiService.checkTerms();

      if (!mounted) return;

      if (termsResult["success"] &&
          termsResult["terms_completed"] == false) {
        Navigator.pushNamedAndRemoveUntil(
          context,
          "/terms",
          (route) => false,
        );
      } else {
        Navigator.pushNamedAndRemoveUntil(
          context,
          "/home",
          (route) => false,
        );
      }
    } else {
      setState(() => _errorMessage = result["message"]);
    }
  }


  // ─────────────────────────────────────────────
  // STEP 1 — FORGOT PASSWORD DIALOG
  // User enters email and new password
  // Calls POST /auth/forgot-password to send OTP
  // ─────────────────────────────────────────────
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
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(20)),
            contentPadding: EdgeInsets.zero,
            backgroundColor: Colors.white,
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [

                  // ── Header ──
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(vertical: 22),
                    decoration: const BoxDecoration(
                      color: Color(0xFF0A1B6F),
                      borderRadius: BorderRadius.vertical(
                          top: Radius.circular(20)),
                    ),
                    child: const Column(
                      children: [
                        Icon(Icons.lock_reset,
                            color: Colors.white, size: 36),
                        SizedBox(height: 8),
                        Text(
                          'Reset Password',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),

                  // ── Body ──
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
                            style: TextStyle(
                              fontSize: 13,
                              color: Colors.black87,
                              height: 1.5,
                            ),
                          ),

                          const SizedBox(height: 18),

                          // ── Email ──
                          const Text(
                            'Registered Email',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF0A1B6F),
                            ),
                          ),
                          const SizedBox(height: 6),
                          TextFormField(
                            controller: _forgotEmailController,
                            keyboardType: TextInputType.emailAddress,
                            decoration: _dialogInputDecoration(
                                'example@gmail.com'),
                            validator: (v) {
                              if (v == null || v.isEmpty) {
                                return 'Please enter your email';
                              }
                              if (!RegExp(r'^[^@]+@[^@]+\.[^@]+')
                                  .hasMatch(v)) {
                                return 'Enter a valid email';
                              }
                              return null;
                            },
                          ),

                          const SizedBox(height: 14),

                          // ── New Password ──
                          const Text(
                            'New Password',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF0A1B6F),
                            ),
                          ),
                          const SizedBox(height: 6),
                          TextFormField(
                            controller: _forgotNewPasswordController,
                            obscureText: _obscureNew,
                            decoration: _dialogInputDecoration(
                              'Enter new password',
                              suffix: IconButton(
                                icon: Icon(
                                  _obscureNew
                                      ? Icons.visibility_off
                                      : Icons.visibility,
                                  size: 18,
                                  color: Colors.grey,
                                ),
                                onPressed: () => setDialogState(
                                    () => _obscureNew = !_obscureNew),
                              ),
                            ),
                            validator: (v) {
                              if (v == null || v.isEmpty) {
                                return 'Please enter a new password';
                              }
                              if (v.length < 8) {
                                return 'Minimum 8 characters';
                              }
                              if (!RegExp(r'[A-Z]').hasMatch(v)) {
                                return 'Must contain an uppercase letter';
                              }
                              if (!RegExp(r'[a-z]').hasMatch(v)) {
                                return 'Must contain a lowercase letter';
                              }
                              if (!RegExp(r'[0-9]').hasMatch(v)) {
                                return 'Must contain a digit';
                              }
                              if (!RegExp(r'[!@#\$%^&*()_+\-=\[\]{}|]')
                                  .hasMatch(v)) {
                                return 'Must contain a special character';
                              }
                              return null;
                            },
                          ),

                          const SizedBox(height: 14),

                          // ── Confirm Password ──
                          const Text(
                            'Confirm Password',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: Color(0xFF0A1B6F),
                            ),
                          ),
                          const SizedBox(height: 6),
                          TextFormField(
                            controller: _forgotConfirmPasswordController,
                            obscureText: _obscureConfirm,
                            decoration: _dialogInputDecoration(
                              'Re-enter new password',
                              suffix: IconButton(
                                icon: Icon(
                                  _obscureConfirm
                                      ? Icons.visibility_off
                                      : Icons.visibility,
                                  size: 18,
                                  color: Colors.grey,
                                ),
                                onPressed: () => setDialogState(() =>
                                    _obscureConfirm = !_obscureConfirm),
                              ),
                            ),
                            validator: (v) {
                              if (v == null || v.isEmpty) {
                                return 'Please confirm your password';
                              }
                              if (v !=
                                  _forgotNewPasswordController.text) {
                                return 'Passwords do not match';
                              }
                              return null;
                            },
                          ),

                          const SizedBox(height: 22),

                          // ── Send OTP Button ──
                          // Calls POST /auth/forgot-password
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton(
                              onPressed: _isSendingReset
                                  ? null
                                  : () async {
                                      if (!(forgotFormKey.currentState
                                              ?.validate() ??
                                          false)) return;

                                      setDialogState(() =>
                                          _isSendingReset = true);

                                      // Call backend forgot password endpoint
                                      final result = await ApiService
                                          .forgotPassword(
                                        email: _forgotEmailController
                                            .text
                                            .trim(),
                                      );

                                      setDialogState(() =>
                                          _isSendingReset = false);

                                      if (!mounted) return;

                                      if (result["success"]) {
                                        // OTP sent — close this dialog
                                        // and open OTP dialog
                                        Navigator.pop(ctx);
                                        _showResetOtpDialog();
                                      } else {
                                        // Show error inside dialog
                                        ScaffoldMessenger.of(context)
                                            .showSnackBar(
                                          SnackBar(
                                            content:
                                                Text(result["message"]),
                                            backgroundColor: Colors.red,
                                          ),
                                        );
                                      }
                                    },
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF0A1B6F),
                                disabledBackgroundColor: Colors.grey[300],
                                padding: const EdgeInsets.symmetric(
                                    vertical: 14),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(10),
                                ),
                              ),
                              child: _isSendingReset
                                  ? const SizedBox(
                                      height: 20,
                                      width: 20,
                                      child: CircularProgressIndicator(
                                        color: Colors.white,
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : const Text(
                                      'Send OTP',
                                      style: TextStyle(
                                        fontSize: 15,
                                        fontWeight: FontWeight.bold,
                                        color: Colors.white,
                                      ),
                                    ),
                            ),
                          ),

                          const SizedBox(height: 8),

                          // ── Cancel ──
                          Center(
                            child: TextButton(
                              onPressed: () => Navigator.pop(ctx),
                              child: const Text(
                                'Cancel',
                                style: TextStyle(
                                    color: Colors.grey, fontSize: 13),
                              ),
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


  // ─────────────────────────────────────────────
  // STEP 2 — RESET OTP DIALOG
  // User enters OTP received in email
  // Calls POST /auth/reset-password to reset password
  // ─────────────────────────────────────────────
  void _showResetOtpDialog() {
    for (final c in _otpControllers) c.clear();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) {
          return AlertDialog(
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(20)),
            contentPadding: EdgeInsets.zero,
            backgroundColor: Colors.white,
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [

                // ── Header ──
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(vertical: 22),
                  decoration: const BoxDecoration(
                    color: Color(0xFF0A1B6F),
                    borderRadius: BorderRadius.vertical(
                        top: Radius.circular(20)),
                  ),
                  child: const Column(
                    children: [
                      Icon(Icons.mark_email_read_outlined,
                          color: Colors.white, size: 36),
                      SizedBox(height: 8),
                      Text(
                        'Verify OTP',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),

                // ── Body ──
                Padding(
                  padding: const EdgeInsets.fromLTRB(24, 20, 24, 8),
                  child: Column(
                    children: [

                      Text(
                        'A 6-digit OTP has been sent to\n${_forgotEmailController.text.trim()}\nEnter it below to reset your password.',
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontSize: 13,
                          color: Colors.black87,
                          height: 1.5,
                        ),
                      ),

                      const SizedBox(height: 20),

                      // ── 6 OTP boxes ──
                      Row(
                        mainAxisAlignment:
                            MainAxisAlignment.spaceBetween,
                        children: List.generate(6, (i) {
                          return SizedBox(
                            width: 42,
                            height: 50,
                            child: TextField(
                              controller: _otpControllers[i],
                              focusNode: _otpFocusNodes[i],
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
                                  borderRadius:
                                      BorderRadius.circular(10),
                                  borderSide: const BorderSide(
                                    color: Color(0xFF0A1B6F),
                                    width: 1.5,
                                  ),
                                ),
                                focusedBorder: OutlineInputBorder(
                                  borderRadius:
                                      BorderRadius.circular(10),
                                  borderSide: const BorderSide(
                                    color: Color(0xFF0A1B6F),
                                    width: 2.5,
                                  ),
                                ),
                                filled: true,
                                fillColor: const Color(0xFFEEF2FF),
                              ),
                              onChanged: (val) {
                                if (val.isNotEmpty && i < 5) {
                                  FocusScope.of(ctx).requestFocus(
                                      _otpFocusNodes[i + 1]);
                                } else if (val.isEmpty && i > 0) {
                                  FocusScope.of(ctx).requestFocus(
                                      _otpFocusNodes[i - 1]);
                                }
                              },
                            ),
                          );
                        }),
                      ),

                      const SizedBox(height: 8),

                      // ── Resend OTP ──
                      // Calls POST /auth/forgot-password again
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton(
                          onPressed: _isResendingOtp
                              ? null
                              : () async {
                                  setDialogState(
                                      () => _isResendingOtp = true);

                                  final result =
                                      await ApiService.forgotPassword(
                                    email: _forgotEmailController.text
                                        .trim(),
                                  );

                                  setDialogState(
                                      () => _isResendingOtp = false);

                                  if (!mounted) return;

                                  ScaffoldMessenger.of(context)
                                      .showSnackBar(
                                    SnackBar(
                                      content: Text(result["message"]),
                                      backgroundColor: result["success"]
                                          ? const Color(0xFF0A1B6F)
                                          : Colors.red,
                                    ),
                                  );
                                },
                          child: _isResendingOtp
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(
                                      strokeWidth: 2),
                                )
                              : const Text(
                                  'Resend OTP',
                                  style: TextStyle(
                                    color: Color(0xFF0A1B6F),
                                    fontWeight: FontWeight.w600,
                                    fontSize: 12,
                                  ),
                                ),
                        ),
                      ),

                      const SizedBox(height: 8),

                      // ── Verify and Reset Button ──
                      // Calls POST /auth/reset-password
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _isVerifyingOtp
                              ? null
                              : () async {
                                  final otp = _otpControllers
                                      .map((c) => c.text)
                                      .join();

                                  if (otp.length < 6) {
                                    ScaffoldMessenger.of(context)
                                        .showSnackBar(
                                      const SnackBar(
                                        content: Text(
                                            'Please enter the full 6-digit OTP.'),
                                        backgroundColor: Colors.red,
                                      ),
                                    );
                                    return;
                                  }

                                  setDialogState(
                                      () => _isVerifyingOtp = true);

                                  // Call backend reset password endpoint
                                  final result =
                                      await ApiService.resetPassword(
                                    email: _forgotEmailController.text
                                        .trim(),
                                    otp: otp,
                                    newPassword:
                                        _forgotNewPasswordController
                                            .text,
                                    confirmPassword:
                                        _forgotConfirmPasswordController
                                            .text,
                                  );

                                  setDialogState(
                                      () => _isVerifyingOtp = false);

                                  if (!mounted) return;

                                  if (result["success"]) {
                                    // Password reset successful
                                    // Close OTP dialog
                                    Navigator.pop(ctx);

                                    // Show success message
                                    ScaffoldMessenger.of(context)
                                        .showSnackBar(
                                      const SnackBar(
                                        content: Text(
                                            'Password reset successfully! Please login with your new password.'),
                                        backgroundColor:
                                            Color(0xFF0A1B6F),
                                      ),
                                    );

                                    // Stay on login page
                                    // User can now login with new password
                                  } else {
                                    // Show error
                                    ScaffoldMessenger.of(context)
                                        .showSnackBar(
                                      SnackBar(
                                        content:
                                            Text(result["message"]),
                                        backgroundColor: Colors.red,
                                      ),
                                    );
                                  }
                                },
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF0A1B6F),
                            disabledBackgroundColor: Colors.grey[300],
                            padding: const EdgeInsets.symmetric(
                                vertical: 14),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(10),
                            ),
                          ),
                          child: _isVerifyingOtp
                              ? const SizedBox(
                                  height: 20,
                                  width: 20,
                                  child: CircularProgressIndicator(
                                    color: Colors.white,
                                    strokeWidth: 2,
                                  ),
                                )
                              : const Text(
                                  'Verify & Reset Password',
                                  style: TextStyle(
                                    fontSize: 15,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.white,
                                  ),
                                ),
                        ),
                      ),

                      const SizedBox(height: 12),

                      // ── Cancel ──
                      TextButton(
                        onPressed: () => Navigator.pop(ctx),
                        child: const Text(
                          'Cancel',
                          style: TextStyle(
                              color: Colors.grey, fontSize: 13),
                        ),
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


  // ── Input decoration helper for dialogs ──────────────────
  InputDecoration _dialogInputDecoration(String hint,
      {Widget? suffix}) {
    return InputDecoration(
      hintText: hint,
      hintStyle: TextStyle(color: Colors.grey[400], fontSize: 13),
      contentPadding:
          const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: BorderSide(color: Colors.grey[300]!),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: BorderSide(color: Colors.grey[300]!),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide:
            const BorderSide(color: Color(0xFF0A1B6F), width: 1.5),
      ),
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

          // ── Background Image ──
          Container(
            decoration: const BoxDecoration(
              image: DecorationImage(
                image: AssetImage('assets/icons/water_background.jpg'),
                fit: BoxFit.cover,
              ),
            ),
          ),
          Container(
            color: Colors.white.withOpacity(0.15),
          ),

          SafeArea(
            child: SingleChildScrollView(
              child: Column(
                children: [
                  const SizedBox(height: 40),

                  // ── Logo ──
                  Transform.scale(
                    scale: 1.8,
                    child: Image.asset(
                      'assets/icons/logo.png',
                      height: 120,
                      fit: BoxFit.contain,
                    ),
                  ),
                  const SizedBox(height: 40),

                  // ── Login Card ──
                  Container(
                    margin:
                        const EdgeInsets.symmetric(horizontal: 24),
                    padding: const EdgeInsets.symmetric(
                        horizontal: 24, vertical: 32),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.75),
                      borderRadius: BorderRadius.circular(20),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.15),
                          blurRadius: 20,
                          offset: const Offset(0, 8),
                        ),
                      ],
                    ),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [

                          // ── Title ──
                          const Center(
                            child: Text(
                              'Login',
                              style: TextStyle(
                                fontSize: 30,
                                fontWeight: FontWeight.bold,
                                color: Color(0xFF1A3A5C),
                              ),
                            ),
                          ),
                          const SizedBox(height: 24),

                          // ── Error Message ──
                          if (_errorMessage.isNotEmpty)
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(12),
                              margin:
                                  const EdgeInsets.only(bottom: 16),
                              decoration: BoxDecoration(
                                color: Colors.red.shade50,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(
                                    color: Colors.red.shade200),
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
                                          color: Colors.red,
                                          fontSize: 13),
                                    ),
                                  ),
                                ],
                              ),
                            ),

                          // ── Email / Phone Label ──
                          const Text(
                            'Email/Phone :',
                            style: TextStyle(
                              fontSize: 13,
                              color: Color(0xFF1A3A5C),
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 6),

                          // ── Email / Phone Input ──
                          TextFormField(
                            controller: _emailController,
                            keyboardType: TextInputType.emailAddress,
                            decoration: InputDecoration(
                              hintText: 'example@gmail.com',
                              hintStyle: TextStyle(
                                  color: Colors.grey[400], fontSize: 13),
                              contentPadding:
                                  const EdgeInsets.symmetric(
                                      horizontal: 14, vertical: 12),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide(
                                    color: Colors.grey[300]!),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide(
                                    color: Colors.grey[300]!),
                              ),
                              filled: true,
                              fillColor: Colors.white,
                            ),
                            validator: (value) {
                              if (value == null ||
                                  value.trim().isEmpty) {
                                return 'Please enter your email or phone';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 14),

                          // ── Password Label ──
                          const Text(
                            'Password',
                            style: TextStyle(
                              fontSize: 13,
                              color: Color(0xFF1A3A5C),
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 6),

                          // ── Password Input ──
                          TextFormField(
                            controller: _passwordController,
                            obscureText: !_passwordVisible,
                            decoration: InputDecoration(
                              hintText: 'Password',
                              hintStyle: TextStyle(
                                  color: Colors.grey[400], fontSize: 13),
                              contentPadding:
                                  const EdgeInsets.symmetric(
                                      horizontal: 14, vertical: 12),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide(
                                    color: Colors.grey[300]!),
                              ),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                                borderSide: BorderSide(
                                    color: Colors.grey[300]!),
                              ),
                              filled: true,
                              fillColor: Colors.white,
                              suffixIcon: IconButton(
                                icon: Icon(
                                  _passwordVisible
                                      ? Icons.visibility_off
                                      : Icons.visibility,
                                  color: Colors.grey,
                                  size: 20,
                                ),
                                onPressed: () => setState(() =>
                                    _passwordVisible =
                                        !_passwordVisible),
                              ),
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Please enter your password';
                              }
                              if (value.length < 8) {
                                return 'Password must be at least 8 characters';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 6),

                          // ── Forgot Password ──
                          Center(
                            child: TextButton(
                              onPressed: _showForgotPasswordDialog,
                              style: TextButton.styleFrom(
                                padding: EdgeInsets.zero,
                                minimumSize: Size.zero,
                                tapTargetSize:
                                    MaterialTapTargetSize.shrinkWrap,
                              ),
                              child: const Text(
                                'Forgot Password?',
                                style: TextStyle(
                                  color: Color(0xFF1A3A5C),
                                  fontSize: 12,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 16),

                          // ── Login Button ──
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton(
                              onPressed: _isLoading ? null : _login,
                              style: ElevatedButton.styleFrom(
                                backgroundColor:
                                    const Color(0xFF1A3A5C),
                                padding: const EdgeInsets.symmetric(
                                    vertical: 14),
                                shape: RoundedRectangleBorder(
                                  borderRadius:
                                      BorderRadius.circular(10),
                                ),
                                elevation: 2,
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
                                  : const Text(
                                      'Log In',
                                      style: TextStyle(
                                        fontSize: 16,
                                        color: Colors.white,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                            ),
                          ),
                          const SizedBox(height: 16),

                          // ── Or continue with ──
                          Center(
                            child: Text(
                              'or continue with',
                              style: TextStyle(
                                color: Colors.grey[600],
                                fontSize: 13,
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),

                          // ── Google Login Button ──
                          Center(
                            child: InkWell(
                              onTap: () {
                                // Google login will be connected later
                              },
                              borderRadius: BorderRadius.circular(50),
                              child: Container(
                                padding: const EdgeInsets.all(10),
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  border: Border.all(
                                      color: Colors.grey[300]!),
                                  color: Colors.white,
                                ),
                                child: Image.asset(
                                  'assets/icons/google_logo.png',
                                  height: 28,
                                  width: 28,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 16),

                          // ── Register Link ──
                          Row(
                            mainAxisAlignment:
                                MainAxisAlignment.center,
                            children: [
                              Text(
                                "Don't have an account?",
                                style: TextStyle(
                                    color: Colors.grey[700],
                                    fontSize: 13),
                              ),
                              TextButton(
                                onPressed: () {
                                  Navigator.pushNamed(
                                      context, '/register');
                                },
                                style: TextButton.styleFrom(
                                  padding:
                                      const EdgeInsets.only(left: 4),
                                  minimumSize: Size.zero,
                                  tapTargetSize:
                                      MaterialTapTargetSize.shrinkWrap,
                                ),
                                child: const Text(
                                  'Register',
                                  style: TextStyle(
                                    color: Color(0xFF1A3A5C),
                                    fontWeight: FontWeight.bold,
                                    fontSize: 13,
                                  ),
                                ),
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