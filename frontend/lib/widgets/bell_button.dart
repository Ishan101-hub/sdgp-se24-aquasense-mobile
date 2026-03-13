import 'package:flutter/material.dart';

// ── Notification model ────────────────────────────────────────
class AppNotification {
  final String title;
  final String message;
  final String type;
  final String time;
  final int targetTabIndex;

  const AppNotification({
    required this.title,
    required this.message,
    required this.type,
    required this.time,
    this.targetTabIndex = 0,
  });
}

// ── Bell Button ───────────────────────────────────────────────
// StatefulWidget so it can track read state and hide red dot
class BellButton extends StatefulWidget {
  final bool hasNotification;
  final List<AppNotification> notifications;
  final void Function(int tabIndex) onSwitchTab;

  const BellButton({
    super.key,
    this.hasNotification = false,
    this.notifications = const [],
    required this.onSwitchTab,
  });

  @override
  State<BellButton> createState() => _BellButtonState();
}

class _BellButtonState extends State<BellButton> {
  // ── Tracks which notification indices have been tapped ──
  final Set<int> _readIndices = {};

  // Red dot visible only when there are unread notifications
  bool get _hasUnread =>
      widget.hasNotification &&
      _readIndices.length < widget.notifications.length;

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.none,
      children: [

        SizedBox(
          width: 56,
          height: 56,
          child: ElevatedButton(
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => NotificationsPage(
                    notifications: widget.notifications,
                    readIndices: _readIndices,
                    onSwitchTab: widget.onSwitchTab,
                    // ── Called back when user taps a notification ──
                    // Marks that index as read → may hide red dot
                    onNotificationRead: (index) {
                      setState(() {
                        _readIndices.add(index);
                      });
                    },
                  ),
                ),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF1A1A6E),
              foregroundColor: Colors.white,
              padding: EdgeInsets.zero,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              elevation: 6,
              shadowColor: const Color(0xFF1A1A6E).withValues(alpha: 0.4),
              overlayColor: Colors.white.withValues(alpha: 0.2),
            ),
            child: const Center(
              child: Icon(
                Icons.notifications_outlined,
                size: 28,
                color: Colors.white,
              ),
            ),
          ),
        ),

      ],
    );
  }
}


// ── Notifications Page ────────────────────────────────────────
class NotificationsPage extends StatefulWidget {
  final List<AppNotification> notifications;
  final Set<int> readIndices;
  final void Function(int tabIndex) onSwitchTab;
  final void Function(int index) onNotificationRead;

  const NotificationsPage({
    super.key,
    this.notifications = const [],
    required this.readIndices,
    required this.onSwitchTab,
    required this.onNotificationRead,
  });

  @override
  State<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<NotificationsPage> {
  // Local copy so UI updates instantly when tapped
  late Set<int> _localReadIndices;

  @override
  void initState() {
    super.initState();
    _localReadIndices = Set.from(widget.readIndices);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFEEF4FF),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A1A6E),
        foregroundColor: Colors.white,
        title: Row(
          children: [
            const Text(
              'Notifications',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            // Badge count shows only UNREAD
            if (widget.notifications.length - _localReadIndices.length > 0) ...[
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.red,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  '${widget.notifications.length - _localReadIndices.length}',
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),

      body: widget.notifications.isEmpty
          ? const Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.notifications_none, size: 80, color: Color(0xFF1A1A6E)),
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
                    'When a leak or over-usage is detected,\nyou will see alerts here.',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 13, color: Color(0xFF888888)),
                  ),
                ],
              ),
            )
          : ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: widget.notifications.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                final notif = widget.notifications[index];
                final bool isRead = _localReadIndices.contains(index);
                return _NotificationItem(
                  notification: notif,
                  isRead: isRead,
                  onTap: () {
                    // ── Mark as read locally (UI updates instantly) ──
                    setState(() => _localReadIndices.add(index));

                    // ── Tell BellButton to update its red dot ──
                    widget.onNotificationRead(index);

                    // ── Navigate to correct page ──
                    widget.onSwitchTab(notif.targetTabIndex);
                    Navigator.of(context).popUntil((route) => route.isFirst);
                  },
                );
              },
            ),
    );
  }
}


// ── Single Notification Item ──────────────────────────────────
class _NotificationItem extends StatelessWidget {
  final AppNotification notification;
  final bool isRead;       // ← greyed out when already read
  final VoidCallback onTap;

  const _NotificationItem({
    required this.notification,
    required this.isRead,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final bool isLeak       = notification.type == 'leak';
    final Color accentColor = isLeak
        ? const Color(0xFFD80B0B)
        : const Color(0xFFE6A817);
    // Faded when read
    final Color itemColor   = isRead
        ? accentColor.withValues(alpha: 0.4)
        : accentColor;
    final Color borderColor = itemColor.withValues(alpha: 0.3);
    final IconData icon     = isLeak
        ? Icons.water_damage_outlined
        : Icons.speed_outlined;
    final String navHint    = isLeak ? 'Go to Leakages →' : 'Go to Home →';

    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          // Slightly grey background when read
          color: isRead ? const Color(0xFFF5F5F5) : Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: borderColor, width: 1.5),
          boxShadow: [
            BoxShadow(
              color: itemColor.withValues(alpha: 0.06),
              blurRadius: 8,
              offset: const Offset(0, 3),
            ),
          ],
        ),
        padding: const EdgeInsets.all(14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [

            // Icon (faded when read)
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                color: itemColor,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: Colors.white, size: 24),
            ),

            const SizedBox(width: 12),

            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [

                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          notification.title,
                          style: TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.bold,
                            color: itemColor,
                          ),
                        ),
                      ),
                      // "Read" badge when tapped
                      if (isRead)
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: Colors.grey.shade200,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Text(
                            'Read',
                            style: TextStyle(
                              fontSize: 10,
                              color: Colors.grey,
                            ),
                          ),
                        ),
                    ],
                  ),

                  const SizedBox(height: 5),

                  Text(
                    notification.message,
                    style: TextStyle(
                      fontSize: 12,
                      color: isRead
                          ? const Color(0xFF888888)
                          : const Color(0xFF444444),
                      height: 1.45,
                    ),
                  ),

                  const SizedBox(height: 8),

                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        notification.time,
                        style: const TextStyle(
                          fontSize: 11,
                          color: Color(0xFF888888),
                        ),
                      ),
                      if (!isRead)
                        Text(
                          navHint,
                          style: TextStyle(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: accentColor,
                          ),
                        ),
                    ],
                  ),

                ],
              ),
            ),

          ],
        ),
      ),
    );
  }
}