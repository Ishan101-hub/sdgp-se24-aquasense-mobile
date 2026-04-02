// lib/widgets/bell_button.dart
// AquaSense — Notification bell widget
//
// Uses ApiService.fetchNotifications() — same baseUrl and auth token
// as every other screen. No separate URL or HTTP logic here.

import 'dart:async';
import 'package:flutter/material.dart';

import '../models/mobile_models.dart';
import '../services/api_service.dart';

// ── Bell Button ───────────────────────────────────────────────

class BellButton extends StatefulWidget {
  final void Function(int tabIndex) onSwitchTab;

  const BellButton({
    super.key,
    required this.onSwitchTab,
  });

  @override
  State<BellButton> createState() => _BellButtonState();
}

class _BellButtonState extends State<BellButton> {
  List<MobileNotification> _notifications = [];
  final Set<int>        _readIndices   = {};
  Timer?                _timer;
  final _api = ApiService();

  bool get _hasUnread =>
      _notifications.isNotEmpty &&
      _readIndices.length < _notifications.length;

  @override
  void initState() {
    super.initState();
    _fetchNotifications();
    // Poll every 15 seconds — backend only returns leak+auto-close events
    _timer = Timer.periodic(
      const Duration(seconds: 15),
      (_) => _fetchNotifications(),
    );
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _fetchNotifications() async {
    try {
      // Uses ApiService — correct baseUrl + JWT token, same as all other screens
      final data = await _api.fetchNotifications();
      if (mounted) {
        setState(() {
          _notifications = data;
          // Remove stale read indices if list shrank
          _readIndices.removeWhere((i) => i >= _notifications.length);
        });
      }
    } catch (_) {
      // Silent fail — don't disrupt UI for background poll
    }
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      clipBehavior: Clip.none,
      children: [

        SizedBox(
          width:  56,
          height: 56,
          child: ElevatedButton(
            onPressed: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => NotificationsPage(
                    notifications:      _notifications,
                    readIndices:        _readIndices,
                    onSwitchTab:        widget.onSwitchTab,
                    onNotificationRead: (index) {
                      setState(() => _readIndices.add(index));
                    },
                  ),
                ),
              );
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF1A1A6E),
              foregroundColor: Colors.white,
              padding:         EdgeInsets.zero,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              elevation:   6,
              shadowColor: const Color(0xFF1A1A6E).withValues(alpha: 0.4),
            ),
            child: const Icon(
              Icons.notifications_outlined,
              size:  28,
              color: Colors.white,
            ),
          ),
        ),

        // Red badge — only shown when there are unread notifications
        if (_hasUnread)
          Positioned(
            top:   -4,
            right: -4,
            child: Container(
              width:  18,
              height: 18,
              decoration: const BoxDecoration(
                color: Colors.red,
                shape: BoxShape.circle,
              ),
              child: Center(
                child: Text(
                  '${_notifications.length - _readIndices.length}',
                  style: const TextStyle(
                    color:      Colors.white,
                    fontSize:   9,
                    fontWeight: FontWeight.bold,
                  ),
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
  final List<MobileNotification> notifications;
  final Set<int>              readIndices;
  final void Function(int)    onSwitchTab;
  final void Function(int)    onNotificationRead;

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
  late Set<int> _localReadIndices;

  @override
  void initState() {
    super.initState();
    _localReadIndices = Set.from(widget.readIndices);
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final int unread = widget.notifications.length - _localReadIndices.length;

    return Scaffold(
      backgroundColor: isDark
          ? const Color(0xFF121212)
          : const Color(0xFFEEF4FF),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A1A6E),
        foregroundColor: Colors.white,
        title: Row(
          children: [
            const Text('Notifications',
                style: TextStyle(fontWeight: FontWeight.bold)),
            if (unread > 0) ...[
              const SizedBox(width: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color:        Colors.red,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text('$unread',
                    style: const TextStyle(
                        fontSize: 12, fontWeight: FontWeight.bold,
                        color: Colors.white)),
              ),
            ],
          ],
        ),
      ),

      body: widget.notifications.isEmpty
          // ── Empty state ───────────────────────────────────────
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.notifications_none,
                      size:  80,
                      color: isDark
                          ? Colors.white30
                          : const Color(0xFF1A1A6E)),
                  const SizedBox(height: 16),
                  Text('No notifications',
                      style: TextStyle(
                        fontSize:   18,
                        fontWeight: FontWeight.bold,
                        color: isDark
                            ? Colors.white54
                            : const Color(0xFF1A1A6E),
                      )),
                  const SizedBox(height: 8),
                  Text(
                    'You will be notified when a leak\nis detected and valve is closed.',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 13,
                      color: isDark
                          ? Colors.white38
                          : const Color(0xFF888888),
                    ),
                  ),
                ],
              ),
            )
          // ── Notification list ─────────────────────────────────
          : ListView.separated(
              padding:          const EdgeInsets.all(16),
              itemCount:        widget.notifications.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (context, index) {
                final notif  = widget.notifications[index];
                final isRead = _localReadIndices.contains(index);
                return _NotificationCard(
                  notification: notif,
                  isRead:       isRead,
                  isDark:       isDark,
                  onTap: () {
                    setState(() => _localReadIndices.add(index));
                    widget.onNotificationRead(index);
                    widget.onSwitchTab(notif.targetTabIndex);
                    Navigator.of(context).popUntil((r) => r.isFirst);
                  },
                );
              },
            ),
    );
  }
}


// ── Notification Card ─────────────────────────────────────────

class _NotificationCard extends StatelessWidget {
  final MobileNotification notification;
  final bool            isRead;
  final bool            isDark;
  final VoidCallback    onTap;

  const _NotificationCard({
    required this.notification,
    required this.isRead,
    required this.isDark,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    const Color accentColor = Color(0xFFD80B0B);
    final Color itemColor   = isRead
        ? accentColor.withValues(alpha: 0.4)
        : accentColor;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: isRead
              ? (isDark ? const Color(0xFF2A2A2A) : const Color(0xFFF5F5F5))
              : (isDark ? const Color(0xFF1E1E1E) : Colors.white),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
              color: itemColor.withValues(alpha: 0.3), width: 1.5),
          boxShadow: [
            BoxShadow(
              color:      itemColor.withValues(alpha: 0.07),
              blurRadius: 8,
              offset:     const Offset(0, 3),
            ),
          ],
        ),
        padding: const EdgeInsets.all(14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [

            Container(
              width:  46,
              height: 46,
              decoration: BoxDecoration(
                color:        itemColor,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Icon(Icons.water_damage_outlined,
                  color: Colors.white, size: 24),
            ),

            const SizedBox(width: 12),

            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [

                  Row(
                    children: [
                      Expanded(
                        child: Text(notification.title,
                            style: TextStyle(
                              fontSize:   14,
                              fontWeight: FontWeight.bold,
                              color:      itemColor,
                            )),
                      ),
                      if (isRead)
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: isDark
                                ? Colors.grey.shade800
                                : Colors.grey.shade200,
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Text('Read',
                              style: TextStyle(
                                  fontSize: 10, color: Colors.grey)),
                        ),
                    ],
                  ),

                  const SizedBox(height: 5),

                  // Dynamic message from backend
                  Text(notification.message,
                      style: TextStyle(
                        fontSize: 12,
                        height:   1.45,
                        color: isRead
                            ? (isDark
                                ? Colors.white38
                                : const Color(0xFF888888))
                            : (isDark
                                ? Colors.white70
                                : const Color(0xFF444444)),
                      )),

                  const SizedBox(height: 8),

                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(notification.time,
                          style: TextStyle(
                            fontSize: 11,
                            color: isDark
                                ? Colors.white38
                                : const Color(0xFF888888),
                          )),
                      if (!isRead)
                        const Text('View Leakages →',
                            style: TextStyle(
                              fontSize:   11,
                              fontWeight: FontWeight.w700,
                              color:      Color(0xFFD80B0B),
                            )),
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
