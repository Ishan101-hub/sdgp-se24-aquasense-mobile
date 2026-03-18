import 'package:flutter/material.dart';

class ServiceCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final VoidCallback onTap;

  const ServiceCard({
    super.key,
    required this.icon,
    required this.title,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final double screenWidth = MediaQuery.of(context).size.width;
    final double scale = screenWidth / 393;

    // AquaSense Custom Dark Palette
    final Color cardColor = isDark ? const Color(0xFF101945) : Colors.white;
    final Color iconColor = isDark
        ? const Color(0xFF64B5F6)
        : const Color(0xFF0A1B6F);
    final Color textColor = isDark
        ? Colors.white.withOpacity(0.9)
        : Colors.black87;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20 * scale),
      child: Container(
        padding: EdgeInsets.all(15 * scale),
        decoration: BoxDecoration(
          color: cardColor,
          borderRadius: BorderRadius.circular(20 * scale),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(isDark ? 0.4 : 0.05),
              blurRadius: 12 * scale,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 42 * scale, color: iconColor),
            SizedBox(height: 12 * scale),
            Text(
              title,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontWeight: FontWeight.bold,
                fontSize: 14 * scale,
                color: textColor,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
