import 'package:flutter/material.dart';

class BellButton extends StatelessWidget {
  final bool hasNotification;

  const BellButton({
    super.key,
    this.hasNotification = false,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.none,
      children: [

        // ── REAL TAPPABLE BUTTON with centered icon ──
        SizedBox(
          width: 56,
          height: 56,
          child: ElevatedButton(
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => const NotificationsPage(),
                ),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF1A1A6E),
              foregroundColor: Colors.white,
              // ── Remove all padding so icon sits perfectly centered ──
              padding: EdgeInsets.zero,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              elevation: 6,
              shadowColor: const Color(0xFF1A1A6E).withValues(alpha: 0.4),
              overlayColor: Colors.white.withValues(alpha: 0.2),
            ),
            // ── Center widget ensures icon is perfectly centered ──
            child: const Center(
              child: Icon(
                Icons.notifications_outlined,
                size: 28,
                color: Colors.white,
              ),
            ),
          ),
        ),

        // ── RED DOT (hidden for now) ──
        if (hasNotification)
          Positioned(
            top: -4,
            right: -4,
            child: Container(
              width: 16,
              height: 16,
              decoration: const BoxDecoration(
                color: Colors.red,
                shape: BoxShape.circle,
              ),
            ),
          ),

      ],
    );
  }
}


// ── NOTIFICATIONS PAGE ───────────────────────────────────────
class NotificationsPage extends StatelessWidget {
  const NotificationsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFEEF4FF),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A1A6E),
        foregroundColor: Colors.white,
        title: const Text(
          'Notifications',
          style: TextStyle(
            fontWeight: FontWeight.bold,
          ),
        ),
      ),
      body: const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.notifications_none,
              size: 80,
              color: Color(0xFF1A1A6E),
            ),
            SizedBox(height: 16),
            Text(
              'No notifications yet',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Color(0xFF1A1A6E),
              ),
            ),
            SizedBox(height: 8),
            Text(
              'When a leak is detected,\nyou will see alerts here.',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 13,
                color: Color(0xFF888888),
              ),
            ),
          ],
        ),
      ),
    );
  }
}