import 'package:flutter/material.dart';
import 'package:aqua_sense/services/auth_service.dart';
import 'package:aqua_sense/services/auth_storage.dart';

class SplashScreen extends StatefulWidget {
  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _fadeAnim;
  late Animation<double> _scaleAnim;

  @override
  void initState() {
    super.initState();

    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );

    _fadeAnim = Tween<double>(
      begin: 0,
      end: 1,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeIn));

    _scaleAnim = Tween<double>(
      begin: 0.8,
      end: 1.0,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOut));

    _controller.forward();
    _navigateAfterSplash();
  }

  // void _navigateToRegistration() async {
  //   await Future.delayed(const Duration(seconds: 3));

  //   if (!mounted) return;

  //   Navigator.pushReplacementNamed(context, '/register');
  // }

  void _navigateAfterSplash() async {
  await Future.delayed(const Duration(seconds: 3));

  if (!mounted) return;

  // AuthService uses FlutterSecureStorage — check access token directly
  final String? token = await AuthService.getAccessToken();

  if (token == null) {
    // No token ever saved → first-time user
    Navigator.pushReplacementNamed(context, '/register');
  } else {
    // Token exists → verify it's still valid with a lightweight API call
    final result = await AuthService.getProfile();

    if (result['success'] == true) {
      Navigator.pushReplacementNamed(context, '/home');
    } else {
      // Token expired or rejected by server
      await AuthService.clearTokens();
      Navigator.pushReplacementNamed(context, '/login');
    }
  }
}

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
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
          Container(color: const Color(0xFF020D2A).withOpacity(0.72)),
          Center(
            child: FadeTransition(
              opacity: _fadeAnim,
              child: ScaleTransition(
                scale: _scaleAnim,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Image.asset('assets/icons/logo.png', height: 150),
                    const SizedBox(height: 20),
                    const Text(
                      'AquaSense',
                      style: TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                        letterSpacing: 1.5,
                      ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Smart Water. Smarter Living.',
                      style: TextStyle(
                        fontSize: 13,
                        color: Colors.white60,
                        letterSpacing: 1.2,
                      ),
                    ),
                    const SizedBox(height: 40),
                    SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(
                        color: Colors.white54,
                        strokeWidth: 2,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
