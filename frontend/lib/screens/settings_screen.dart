import 'package:flutter/material.dart';
import 'profile_screen.dart';
import 'security_screen.dart';
import 'theme_screen.dart';
import 'terms_screen.dart';
import 'login_page.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  void _showLogoutDialog(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        contentPadding: EdgeInsets.zero,
        backgroundColor: isDark ? const Color(0xFF1E1E1E) : Colors.white,
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 22),
              decoration: const BoxDecoration(
                color: Color(0xFF0A1B6F),
                borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
              ),
              child: const Column(
                children: [
                  Icon(Icons.logout, color: Colors.white, size: 36),
                  SizedBox(height: 8),
                  Text(
                    'Log Out',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.bold),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 20, 24, 8),
              child: Column(
                children: [
                  Text(
                    'Are you sure you want to log out of AquaSense?',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                        fontSize: 14,
                        color: isDark ? Colors.white70 : Colors.black87,
                        height: 1.5),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Your device sensors will continue running in the background.',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 12, color: Colors.grey, height: 1.4),
                  ),
                  const SizedBox(height: 22),
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: () => Navigator.pop(ctx),
                          style: OutlinedButton.styleFrom(
                            side: const BorderSide(color: Color(0xFF0A1B6F)),
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(10)),
                            padding: const EdgeInsets.symmetric(vertical: 13),
                          ),
                          child: const Text(
                            'Cancel',
                            style: TextStyle(
                                color: Color(0xFF0A1B6F),
                                fontWeight: FontWeight.w600),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: ElevatedButton(
                          onPressed: () {
                            Navigator.pop(ctx);
                            Navigator.pushAndRemoveUntil(
                              context,
                              MaterialPageRoute(
                                  builder: (_) => LoginPage()),
                              (route) => false,
                            );
                          },
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.red,
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(10)),
                            padding: const EdgeInsets.symmetric(vertical: 13),
                          ),
                          child: const Text(
                            'Log Out',
                            style: TextStyle(
                                color: Colors.white,
                                fontWeight: FontWeight.w600),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF121212) : Colors.grey[100],
      body: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(16, 20, 16, 20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.only(left: 4, bottom: 12),
              child: Text(
                'Settings',
                style: TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.bold,
                  color: isDark ? Colors.white : const Color(0xFF0A1B6F),
                ),
              ),
            ),

            InkWell(
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => const ProfileScreen()),
              ),
              borderRadius: BorderRadius.circular(20),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1E1E1E) : Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.08),
                      blurRadius: 10,
                      offset: const Offset(0, 4),
                    ),
                  ],
                  border: Border.all(color: const Color(0xFF0A1B6F), width: 2),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 72,
                      height: 72,
                      decoration: const BoxDecoration(
                        color: Color(0xFF0A1B6F),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.person,
                          size: 38, color: Colors.white),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Profile',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: isDark
                                  ? Colors.white
                                  : const Color(0xFF0A1B6F),
                            ),
                          ),
                          const SizedBox(height: 2),
                          const Text(
                            'View and edit your profile',
                            style:
                                TextStyle(fontSize: 12, color: Colors.grey),
                          ),
                        ],
                      ),
                    ),
                    const Icon(Icons.chevron_right,
                        color: Colors.grey, size: 26),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 20),

            Container(
              width: double.infinity,
              decoration: BoxDecoration(
                color: isDark ? const Color(0xFF1E1E1E) : Colors.white,
                borderRadius: BorderRadius.circular(20),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.08),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Column(
                children: [
                  _buildRow(
                    context,
                    icon: Icons.shield_outlined,
                    iconBg: const Color(0xFFE8EAFB),
                    iconColor: const Color(0xFF3949AB),
                    title: 'Security',
                    subtitle: 'Password, 2FA, biometrics',
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                          builder: (_) => const SecurityScreen()),
                    ),
                  ),
                  _buildDivider(),
                  _buildRow(
                    context,
                    icon: Icons.palette_outlined,
                    iconBg: const Color(0xFFE8F5E9),
                    iconColor: const Color(0xFF388E3C),
                    title: 'Theme',
                    subtitle: 'Light, dark, display settings',
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                          builder: (_) => const ThemeScreen()),
                    ),
                  ),
                  _buildDivider(),
                  _buildRow(
                    context,
                    icon: Icons.description_outlined,
                    iconBg: const Color(0xFFFFF8E1),
                    iconColor: const Color(0xFFF9A825),
                    title: 'Terms & Conditions',
                    subtitle: 'Privacy policy and agreements',
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                          builder: (_) => const TermsScreen()),
                    ),
                  ),
                  _buildDivider(),
                  _buildRow(
                    context,
                    icon: Icons.logout,
                    iconBg: const Color(0xFFFFEBEE),
                    iconColor: Colors.red,
                    title: 'Logout',
                    subtitle: 'Sign out of your account',
                    isLogout: true,
                    onTap: () => _showLogoutDialog(context),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRow(
    BuildContext context, {
    required IconData icon,
    required Color iconBg,
    required Color iconColor,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
    bool isLogout = false,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
        child: Row(
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: iconBg,
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(icon, color: iconColor, size: 26),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      color: isLogout
                          ? Colors.red
                          : (isDark ? Colors.white : const Color(0xFF0A1B6F)),
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    subtitle,
                    style: const TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                ],
              ),
            ),
            if (!isLogout)
              const Icon(Icons.chevron_right, color: Colors.grey, size: 24),
          ],
        ),
      ),
    );
  }

  Widget _buildDivider() => const Divider(
        color: Color(0xFFF0F0F0),
        thickness: 1,
        height: 0,
        indent: 16,
        endIndent: 16,
      );
}