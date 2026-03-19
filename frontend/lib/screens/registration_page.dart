import 'package:flutter/material.dart';
import '../services/api_service.dart';

class RegistrationPage extends StatefulWidget {
  const RegistrationPage({super.key});

  @override
  State<RegistrationPage> createState() => _RegistrationPageState();
}

class _RegistrationPageState extends State<RegistrationPage> {
  final _formKey = GlobalKey<FormState>();

  // Controllers to get text from input fields
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _phoneController = TextEditingController();

  // OTP controllers — 6 separate boxes
  final List<TextEditingController> _otpControllers =
      List.generate(6, (_) => TextEditingController());
  final List<FocusNode> _otpFocusNodes =
      List.generate(6, (_) => FocusNode());

  // State variables
  bool _isLoading = false;
  bool _isVerifyingOtp = false;
  bool _isResendingOtp = false;
  bool _passwordVisible = false;
  String _errorMessage = "";

  // Store email after registration so OTP dialog can use it
  String _registeredEmail = "";


  @override
  void dispose() {
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _phoneController.dispose();
    for (final c in _otpControllers) c.dispose();
    for (final f in _otpFocusNodes) f.dispose();
    super.dispose();
  }


  // ─────────────────────────────────────────────
  // REGISTER FUNCTION
  // Called when user clicks Register button
  // Calls POST /auth/register on the backend
  // ─────────────────────────────────────────────
  Future<void> _onRegister() async {
    // Clear any previous error
    setState(() => _errorMessage = "");

    // Validate all form fields
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() => _isLoading = true);

    // Build phone number with country code
    final phone = "+94${_phoneController.text.trim()}";

    // Call the backend register endpoint
    final result = await ApiService.register(
      name: _nameController.text.trim(),
      email: _emailController.text.trim(),
      phone: phone,
      password: _passwordController.text,
    );

    setState(() => _isLoading = false);

    if (result["success"]) {
      // Save email so OTP dialog can use it
      _registeredEmail = _emailController.text.trim();

      // Show OTP dialog
      _showOtpDialog();
    } else {
      // Show error from backend
      setState(() => _errorMessage = result["message"]);
    }
  }


  // ─────────────────────────────────────────────
  // VERIFY OTP FUNCTION
  // Called when user clicks Verify and Continue in OTP dialog
  // After verification automatically logs in user
  // No need to login manually after registering
  // ─────────────────────────────────────────────
  Future<void> _verifyOtp(StateSetter setDialogState) async {
    // Combine all 6 OTP boxes into one string
    final otp = _otpControllers.map((c) => c.text).join();

    if (otp.length < 6) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter the full 6-digit OTP.'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setDialogState(() => _isVerifyingOtp = true);

    // Step 1 — Verify the OTP with backend
    final verifyResult = await ApiService.verifyOtp(
      email: _registeredEmail,
      otp: otp,
    );

    if (!verifyResult["success"]) {
      // OTP wrong or expired — show error and stay on dialog
      setDialogState(() => _isVerifyingOtp = false);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(verifyResult["message"]),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    // Step 2 — Automatically login after OTP verified
    // User does not need to go to login page manually
    final loginResult = await ApiService.login(
      email: _registeredEmail,
      password: _passwordController.text,
    );

    setDialogState(() => _isVerifyingOtp = false);

    if (!mounted) return;

    // Close the OTP dialog
    Navigator.pop(context);

    if (loginResult["success"]) {
      // Step 3 — Check if terms are completed
      final termsResult = await ApiService.checkTerms();

      if (!mounted) return;

      if (termsResult["success"] &&
          termsResult["terms_completed"] == false) {
        // Terms not accepted yet — show terms page
        Navigator.pushNamedAndRemoveUntil(
          context,
          '/terms',
          (route) => false,
        );
      } else {
        // Terms already done — go directly to home
        Navigator.pushNamedAndRemoveUntil(
          context,
          '/home',
          (route) => false,
        );
      }
    } else {
      // Auto login failed — fall back to login page
      Navigator.pushNamedAndRemoveUntil(
        context,
        '/login',
        (route) => false,
      );
    }
  }


  // ─────────────────────────────────────────────
  // RESEND OTP FUNCTION
  // Called when user clicks Resend OTP
  // Calls POST /auth/resend-otp on the backend
  // ─────────────────────────────────────────────
  Future<void> _resendOtp(StateSetter setDialogState) async {
    setDialogState(() => _isResendingOtp = true);

    final result = await ApiService.resendOtp(email: _registeredEmail);

    setDialogState(() => _isResendingOtp = false);

    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(result["message"]),
        backgroundColor: result["success"]
            ? const Color(0xFF0A1B6F)
            : Colors.red,
      ),
    );
  }


  // ─────────────────────────────────────────────
  // OTP DIALOG
  // Shows after successful registration
  // User enters the OTP received in their email
  // ─────────────────────────────────────────────
  void _showOtpDialog() {
    // Clear any previous OTP input
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
                        'Verify Your Email',
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

                      // Shows which email OTP was sent to
                      Text(
                        'A 6-digit OTP has been sent to\n$_registeredEmail\nEnter it below to complete your registration.',
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
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
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
                                  borderRadius: BorderRadius.circular(10),
                                  borderSide: const BorderSide(
                                    color: Color(0xFF0A1B6F),
                                    width: 1.5,
                                  ),
                                ),
                                focusedBorder: OutlineInputBorder(
                                  borderRadius: BorderRadius.circular(10),
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
                                  // Move to next box automatically
                                  FocusScope.of(ctx).requestFocus(
                                      _otpFocusNodes[i + 1]);
                                } else if (val.isEmpty && i > 0) {
                                  // Move back on delete
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
                      Align(
                        alignment: Alignment.centerRight,
                        child: TextButton(
                          onPressed: _isResendingOtp
                              ? null
                              : () => _resendOtp(setDialogState),
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

                      // ── Verify Button ──
                      // Shows spinner while verifying and auto logging in
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton(
                          onPressed: _isVerifyingOtp
                              ? null
                              : () => _verifyOtp(setDialogState),
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
                                  'Verify & Continue',
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
                            color: Colors.grey,
                            fontSize: 13,
                          ),
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
                  const SizedBox(height: 15),

                  // ── Logo ──
                  Transform.scale(
                    scale: 1.2,
                    child: Image.asset(
                      'assets/icons/logo.png',
                      height: 180,
                      fit: BoxFit.contain,
                    ),
                  ),
                  const SizedBox(height: 15),

                  // ── Registration Card ──
                  Container(
                    margin: const EdgeInsets.symmetric(horizontal: 24),
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
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [

                          // ── Title ──
                          const Center(
                            child: Text(
                              'Register',
                              style: TextStyle(
                                fontSize: 30,
                                fontWeight: FontWeight.bold,
                                color: Color(0xFF1A3A5C),
                              ),
                            ),
                          ),
                          const SizedBox(height: 24),

                          // ── Error Message ──
                          // Only shown when backend returns an error
                          if (_errorMessage.isNotEmpty)
                            Container(
                              width: double.infinity,
                              padding: const EdgeInsets.all(12),
                              margin: const EdgeInsets.only(bottom: 16),
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

                          // ── Full Name ──
                          _buildLabel('Full Name'),
                          const SizedBox(height: 6),
                          TextFormField(
                            controller: _nameController,
                            textCapitalization: TextCapitalization.words,
                            decoration:
                                _inputDecoration('Enter your full name'),
                            validator: (value) {
                              if (value == null || value.trim().isEmpty) {
                                return 'Please enter your full name';
                              }
                              if (value.trim().length < 2) {
                                return 'Name must be at least 2 characters';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 14),

                          // ── Email ──
                          _buildLabel('Email'),
                          const SizedBox(height: 6),
                          TextFormField(
                            controller: _emailController,
                            keyboardType: TextInputType.emailAddress,
                            decoration:
                                _inputDecoration('example@gmail.com'),
                            validator: (value) {
                              if (value == null || value.trim().isEmpty) {
                                return 'Please enter your email';
                              }
                              if (!RegExp(r'^[^@]+@[^@]+\.[^@]+')
                                  .hasMatch(value.trim())) {
                                return 'Please enter a valid email';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 14),

                          // ── Password ──
                          _buildLabel('Password'),
                          const SizedBox(height: 6),
                          TextFormField(
                            controller: _passwordController,
                            obscureText: !_passwordVisible,
                            decoration:
                                _inputDecoration('Password').copyWith(
                              suffixIcon: IconButton(
                                icon: Icon(
                                  _passwordVisible
                                      ? Icons.visibility_off
                                      : Icons.visibility,
                                  color: Colors.grey,
                                  size: 20,
                                ),
                                onPressed: () => setState(() =>
                                    _passwordVisible = !_passwordVisible),
                              ),
                            ),
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Please enter a password';
                              }
                              if (value.length < 8) {
                                return 'Password must be at least 8 characters';
                              }
                              if (!RegExp(r'[A-Z]').hasMatch(value)) {
                                return 'Password must contain at least one uppercase letter';
                              }
                              if (!RegExp(r'[a-z]').hasMatch(value)) {
                                return 'Password must contain at least one lowercase letter';
                              }
                              if (!RegExp(r'[0-9]').hasMatch(value)) {
                                return 'Password must contain at least one digit';
                              }
                              if (!RegExp(r'[!@#\$%^&*()_+\-=\[\]{}|]')
                                  .hasMatch(value)) {
                                return 'Password must contain at least one special character';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 14),

                          // ── Phone Number ──
                          _buildLabel('Phone Number'),
                          const SizedBox(height: 6),
                          Row(
                            children: [
                              // Country code — fixed at +94
                              SizedBox(
                                width: 70,
                                child: TextFormField(
                                  initialValue: '+94',
                                  enabled: false,
                                  textAlign: TextAlign.center,
                                  decoration: InputDecoration(
                                    contentPadding:
                                        const EdgeInsets.symmetric(
                                            horizontal: 8, vertical: 12),
                                    border: OutlineInputBorder(
                                      borderRadius:
                                          BorderRadius.circular(8),
                                    ),
                                    filled: true,
                                    fillColor: Colors.grey[300],
                                  ),
                                ),
                              ),
                              const SizedBox(width: 10),
                              // Phone number without country code
                              Expanded(
                                child: TextFormField(
                                  controller: _phoneController,
                                  keyboardType: TextInputType.phone,
                                  decoration:
                                      _inputDecoration('XXXXXXXXX'),
                                  validator: (value) {
                                    if (value == null ||
                                        value.trim().isEmpty) {
                                      return 'Please enter your phone number';
                                    }
                                    if (!RegExp(r'^\d+$')
                                        .hasMatch(value.trim())) {
                                      return 'Phone must contain only digits';
                                    }
                                    if (value.trim().length < 9) {
                                      return 'Please enter a valid phone number';
                                    }
                                    return null;
                                  },
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 24),

                          // ── Register Button ──
                          // Shows spinner while registering
                          // Disabled while loading to prevent double clicks
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton(
                              onPressed:
                                  _isLoading ? null : _onRegister,
                              style: ElevatedButton.styleFrom(
                                backgroundColor: const Color(0xFF1A3A5C),
                                disabledBackgroundColor: Colors.grey[300],
                                padding: const EdgeInsets.symmetric(
                                    vertical: 14),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(10),
                                ),
                              ),
                              child: _isLoading
                                  ? const SizedBox(
                                      height: 20,
                                      width: 20,
                                      child: CircularProgressIndicator(
                                        color: Colors.white,
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : const Text(
                                      'Register',
                                      style: TextStyle(
                                        fontSize: 16,
                                        color: Colors.white,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                            ),
                          ),
                          const SizedBox(height: 16),

                          // ── Login Link ──
                          Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                'Already have an account?',
                                style: TextStyle(
                                    color: Colors.grey[700],
                                    fontSize: 13),
                              ),
                              TextButton(
                                onPressed: () {
                                  Navigator.pushNamed(context, '/login');
                                },
                                child: const Text(
                                  'Log In',
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


  Widget _buildLabel(String text) {
    return Text(
      text,
      style: const TextStyle(
        fontSize: 13,
        color: Color(0xFF1A3A5C),
        fontWeight: FontWeight.w500,
      ),
    );
  }

  InputDecoration _inputDecoration(String hint) {
    return InputDecoration(
      hintText: hint,
      contentPadding:
          const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
      ),
      filled: true,
      fillColor: Colors.white,
    );
  }
}
