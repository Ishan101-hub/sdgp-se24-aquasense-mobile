// lib/screens/home_screen.dart
// AquaSense — Shell screen: header, bottom nav, notification FAB panel.
//
// Notification system v3.4:
//   • Badge count and panel list come from GET /mobile/alerts (resolved=false).
//     This covers ALL unresolved event types: leak_detected, flow_mismatch,
//     valve_failure — not just auto-close events like /mobile/notifications.
//   • Each AlertItem has a real server ID. Tapping an item calls
//     POST /mobile/alerts/{id}/resolve then refreshes the list so the badge
//     count and panel stay in sync with the server.
//   • "Mark all read" resolves every visible alert on the server in parallel.
//   • Badge count uses server-returned unread_count, not a local counter,
//     so it is always accurate even across app restarts.
//   • Poll interval: 15 seconds (unchanged).

import 'dart:async';
import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../models/mobile_models.dart';
import '../widgets/custom_bottom_nav.dart';
import 'settings_screen.dart';
import 'usage_screen.dart';
import 'services_screen.dart';
import 'home_page.dart';
import 'leakages_page.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen>
    with SingleTickerProviderStateMixin {
  int  selectedIndex   = 0;
  bool _showNotifPanel = false;
  String _selectedDistrict = 'Colombo';

  late AnimationController _animController;
  late Animation<double> _fadeAnim;
  late Animation<Offset> _slideAnim;

  // ── Alert / notification state ────────────────────────────────────────────
  // Populated from GET /mobile/alerts (resolved=false).
  // AlertsResponse.unreadCount is the server-authoritative badge count.
  // AlertsResponse.items are the individual unresolved events with real IDs.
  AlertsResponse _alerts = AlertsResponse.empty();

  // Track IDs currently being resolved (to show a loading indicator on the tile)
  final Set<int> _resolvingIds = {};

  final _api       = ApiService();
  Timer? _pollTimer;

  // ── District list ─────────────────────────────────────────────────────────
  final List<String> _sriLankaDistricts = [
    'Ampara', 'Anuradhapura', 'Badulla', 'Batticaloa', 'Colombo',
    'Galle', 'Gampaha', 'Hambantota', 'Jaffna', 'Kalutara', 'Kandy',
    'Kegalle', 'Kilinochchi', 'Kurunegala', 'Mannar', 'Matale',
    'Matara', 'Monaragala', 'Mullaitivu', 'Nuwara Eliya', 'Polonnaruwa',
    'Puttalam', 'Ratnapura', 'Trincomalee', 'Vavuniya',
  ];

  void switchTab(int index) => setState(() => selectedIndex = index);

  List<Widget> get pages => [
    HomePage(onSwitchTab: switchTab),
    LeakagesPage(onSwitchTab: switchTab),
    const UsageScreen(),
    const ServicesScreen(),
    const SettingsScreen(),
  ];

  // ── Lifecycle ─────────────────────────────────────────────────────────────
  @override
  void initState() {
    super.initState();

    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 220),
    );
    _fadeAnim = CurvedAnimation(
        parent: _animController, curve: Curves.easeOut);
    _slideAnim = Tween<Offset>(
      begin: const Offset(0, -0.08),
      end:   Offset.zero,
    ).animate(CurvedAnimation(
        parent: _animController, curve: Curves.easeOut));

    _fetchAlerts();
    _pollTimer = Timer.periodic(
      const Duration(seconds: 15),
      (_) => _fetchAlerts(),
    );
    
    // 1. FOREGROUND LISTENER
    // Triggers if a notification arrives while the app is wide open on screen.
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      debugPrint('Foreground message received: ${message.notification?.title}');
      
      // If a leak alert just arrived, refresh your UI stats immediately!
      if (mounted) {
        _fetchAlerts(); // Re-runs your existing alert list fetch method
      }
    });

    // 2. BACKGROUND TAP LISTENER
    // Triggers when a user pulls down their Android/iOS notification tray and taps the alert.
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      debugPrint('User tapped a background notification!');
      
      // Extract target tab index sent by the Python server payload data, default to index 1 (Alerts Tab)
      final targetTabStr = message.data['target_tab_index'] ?? '1';
      final tabIndex = int.tryParse(targetTabStr) ?? 1;
      
      if (mounted) {
        switchTab(tabIndex); // Triggers your existing tab-switching/navigation method
      }
    });
  
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    _animController.dispose();
    super.dispose();
  }

  // ── Fetch unresolved alerts from server ───────────────────────────────────
  Future<void> _fetchAlerts() async {
    try {
      final response = await _api.fetchAlerts(resolved: false, limit: 50);
      if (!mounted) return;
      setState(() => _alerts = response);
    } catch (_) {
      // Silent — don't disrupt UI for background poll failure
    }
  }

  // ── Resolve a single alert on the server, then refresh ───────────────────
  Future<void> _resolveAlert(AlertItem alert) async {
    if (_resolvingIds.contains(alert.id)) return;
    setState(() => _resolvingIds.add(alert.id));
    try {
      await _api.resolveAlert(alert.id);
      // Navigate to leakages tab (tab index 1) after resolving
      switchTab(alert.targetTabIndex);
      _closePanel();
    } catch (_) {
      // Ignore — the item stays visible so the user can try again
    } finally {
      if (mounted) setState(() => _resolvingIds.remove(alert.id));
      // Always refresh so badge + list are in sync with server
      _fetchAlerts();
    }
  }

  // ── Resolve all visible alerts in parallel ────────────────────────────────
  Future<void> _markAllRead() async {
    final ids = _alerts.items.map((e) => e.id).toList();
    if (ids.isEmpty) return;
    setState(() => _resolvingIds.addAll(ids));
    try {
      await Future.wait(ids.map((id) => _api.resolveAlert(id)));
    } catch (_) {
      // Partial failures are fine — refresh will show remaining items
    } finally {
      if (mounted) {
        setState(() => _resolvingIds.removeAll(ids));
      }
      _fetchAlerts();
    }
  }

  // ── Panel toggle ──────────────────────────────────────────────────────────
  void _toggleNotifPanel() {
    setState(() => _showNotifPanel = !_showNotifPanel);
    _showNotifPanel
        ? _animController.forward()
        : _animController.reverse();
  }

  void _closePanel() {
    _animController.reverse().then((_) {
      if (mounted) setState(() => _showNotifPanel = false);
    });
  }

  // ── Map event_type → display metadata ────────────────────────────────────
  _NotifMeta _metaForEventType(String eventType) {
    switch (eventType) {
      case 'leak_detected':
        return _NotifMeta(
            Icons.water_damage_outlined, Colors.red, 'Leak');
      case 'flow_mismatch':
        return _NotifMeta(
            Icons.warning_amber_outlined, Colors.orange, 'Mismatch');
      case 'valve_failure':
        return _NotifMeta(
            Icons.settings_input_component_outlined,
            Colors.deepOrange, 'Valve Failure');
      case 'valve_opened':
      case 'valve_closed':
        return _NotifMeta(
            Icons.settings_input_component_outlined,
            const Color(0xFF0A1B6F), 'Valve');
      default:
        return _NotifMeta(
            Icons.notifications_outlined, Colors.blueGrey, 'Alert');
    }
  }

  // ── Human-readable title from event_type + zone_name ─────────────────────
  String _titleForAlert(AlertItem alert) {
    switch (alert.eventType) {
      case 'leak_detected':
        return 'Leak Detected: ${alert.zoneName}';
      case 'flow_mismatch':
        return 'Flow Mismatch: ${alert.zoneName}';
      case 'valve_failure':
        return 'Valve Failure: ${alert.zoneName}';
      default:
        return 'Alert: ${alert.zoneName}';
    }
  }

  // ── Relative time from ISO timestamp string ───────────────────────────────
  String _relativeTime(String isoTimestamp) {
    try {
      final dt   = DateTime.parse(isoTimestamp).toLocal();
      final diff = DateTime.now().difference(dt);
      if (diff.inSeconds < 60)  return 'Just now';
      if (diff.inMinutes < 60)  return '${diff.inMinutes} min ago';
      if (diff.inHours   < 24)  return '${diff.inHours} hr ago';
      return '${diff.inDays} day${diff.inDays > 1 ? 's' : ''} ago';
    } catch (_) {
      return '';
    }
  }

  // ── Build ─────────────────────────────────────────────────────────────────
  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final unread = _alerts.unreadCount;

    return Scaffold(
      backgroundColor:
          isDark ? const Color(0xFF121212) : const Color(0xFFEEF4FF),
      body: Stack(
        children: [
          SafeArea(
            child: Column(
              children: [
                _buildHeader(),
                const SizedBox(height: 12),
                Expanded(child: pages[selectedIndex]),
              ],
            ),
          ),

          // Dimmed backdrop when panel is open
          if (_showNotifPanel)
            GestureDetector(
              onTap: _closePanel,
              child: Container(color: Colors.black.withOpacity(0.25)),
            ),

          // Notification panel — positioned above the bottom nav
          if (_showNotifPanel)
            Positioned(
              bottom: 90, right: 14, left: 14,
              child: FadeTransition(
                opacity: _fadeAnim,
                child: SlideTransition(
                  position: _slideAnim,
                  child: _buildNotifPanel(isDark, unread),
                ),
              ),
            ),
        ],
      ),

      // ── FAB — notification bell ──────────────────────────────────────────
      floatingActionButton: Stack(
        clipBehavior: Clip.none,
        children: [
          FloatingActionButton(
            onPressed: _toggleNotifPanel,
            backgroundColor: _showNotifPanel
                ? const Color(0xFF1A3499)
                : const Color(0xFF0B1B66),
            elevation: 8,
            shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16)),
            child: Icon(
              _showNotifPanel
                  ? Icons.notifications_active
                  : Icons.notifications_none,
              color: Colors.white,
            ),
          ),
          // Red badge
          if (unread > 0)
            Positioned(
              right: 6, top: 6,
              child: Container(
                width: 18, height: 18,
                decoration: BoxDecoration(
                  color: Colors.red,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 2),
                ),
                child: Center(
                  child: Text(
                    '$unread',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 9,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),

      bottomNavigationBar: CustomBottomNav(
        currentIndex: selectedIndex,
        onTap: (index) {
          _closePanel();
          setState(() => selectedIndex = index);
        },
      ),
    );
  }

  // ── Header ────────────────────────────────────────────────────────────────
  Widget _buildHeader() {
    return Container(
      width: double.infinity,
      color: const Color(0xFF0B1B66),
      padding: const EdgeInsets.fromLTRB(18, 0, 18, 0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Padding(
            padding: const EdgeInsets.only(left: 12),
            child: Transform.scale(
              scale: 1.8,
              child: Image.asset(
                'assets/icons/headerLogo.png',
                height: 80, fit: BoxFit.contain,
              ),
            ),
          ),
          const Spacer(),
          GestureDetector(
            onTap: _showDistrictPicker,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                    color: Colors.white.withOpacity(0.3), width: 1),
              ),
              child: Row(
                children: [
                  const Icon(Icons.location_on,
                      color: Colors.white, size: 15),
                  const SizedBox(width: 4),
                  Text(_selectedDistrict,
                      style: const TextStyle(
                        color: Colors.white, fontSize: 13,
                        fontWeight: FontWeight.w500,
                      )),
                  const SizedBox(width: 3),
                  const Icon(Icons.keyboard_arrow_down,
                      color: Colors.white, size: 16),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ── Notification panel ────────────────────────────────────────────────────
  Widget _buildNotifPanel(bool isDark, int unread) {
    return Material(
      elevation: 16,
      borderRadius: BorderRadius.circular(22),
      shadowColor: Colors.black38,
      child: Container(
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E1E1E) : Colors.white,
          borderRadius: BorderRadius.circular(22),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [

            // ── Panel header ──────────────────────────────────────────────
            Container(
              padding: const EdgeInsets.symmetric(
                  horizontal: 18, vertical: 14),
              decoration: const BoxDecoration(
                color: Color(0xFF0B1B66),
                borderRadius: BorderRadius.vertical(
                    top: Radius.circular(22)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.notifications,
                      color: Colors.white, size: 20),
                  const SizedBox(width: 8),
                  const Text('Notifications',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 15,
                      )),
                  if (unread > 0) ...[
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 7, vertical: 2),
                      decoration: BoxDecoration(
                        color: Colors.red,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Text('$unread',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                          )),
                    ),
                  ],
                  const Spacer(),
                  if (_alerts.items.isNotEmpty)
                    GestureDetector(
                      onTap: _markAllRead,
                      child: const Text('Mark all read',
                          style: TextStyle(
                              color: Colors.white70,
                              fontSize: 12)),
                    ),
                ],
              ),
            ),

            // ── Alert list or empty state ─────────────────────────────────
            ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 340),
              child: _alerts.items.isEmpty
                  ? _buildEmpty()
                  : ListView.separated(
                      shrinkWrap: true,
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      itemCount: _alerts.items.length,
                      separatorBuilder: (_, __) => const Divider(
                        height: 0, thickness: 0.4,
                        indent: 16, endIndent: 16,
                      ),
                      itemBuilder: (_, i) =>
                          _buildAlertTile(_alerts.items[i], isDark),
                    ),
            ),

            // ── Close footer ──────────────────────────────────────────────
            InkWell(
              onTap: _closePanel,
              borderRadius: const BorderRadius.vertical(
                  bottom: Radius.circular(22)),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 12),
                decoration: BoxDecoration(
                  color: isDark
                      ? const Color(0xFF2A2A2A)
                      : Colors.grey[50],
                  borderRadius: const BorderRadius.vertical(
                      bottom: Radius.circular(22)),
                ),
                child: const Text('Close',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: Color(0xFF0B1B66),
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                    )),
              ),
            ),

          ],
        ),
      ),
    );
  }

  // ── Single alert tile ─────────────────────────────────────────────────────
  Widget _buildAlertTile(AlertItem alert, bool isDark) {
    final meta      = _metaForEventType(alert.eventType);
    final title     = _titleForAlert(alert);
    final timeStr   = _relativeTime(alert.timestamp);
    final resolving = _resolvingIds.contains(alert.id);

    return InkWell(
      onTap: resolving ? null : () => _resolveAlert(alert),
      child: Container(
        // Unread = always true here since we only fetch resolved=false
        color: isDark
            ? Colors.white.withOpacity(0.05)
            : const Color(0xFFF0F3FF),
        padding: const EdgeInsets.symmetric(
            horizontal: 14, vertical: 10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [

            // Icon circle
            Container(
              width: 38, height: 38,
              decoration: BoxDecoration(
                color: meta.color.withOpacity(0.12),
                shape: BoxShape.circle,
              ),
              child: resolving
                  ? const Padding(
                      padding: EdgeInsets.all(10),
                      child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.grey),
                    )
                  : Icon(meta.icon, color: meta.color, size: 19),
            ),

            const SizedBox(width: 10),

            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [

                  // Title row + unread dot
                  Row(
                    children: [
                      Expanded(
                        child: Text(title,
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.bold,
                              color: isDark
                                  ? Colors.white
                                  : const Color(0xFF0A1B6F),
                            )),
                      ),
                      Container(
                        width: 7, height: 7,
                        decoration: const BoxDecoration(
                          color: Colors.red,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 2),

                  // Description from backend
                  if (alert.description != null &&
                      alert.description!.isNotEmpty)
                    Text(
                      alert.description!,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 11.5,
                        color: isDark
                            ? Colors.grey[400]
                            : Colors.grey[600],
                        height: 1.4,
                      ),
                    ),

                  const SizedBox(height: 3),

                  // Type badge + timestamp + tap hint
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: meta.color.withOpacity(0.10),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(meta.label,
                            style: TextStyle(
                              fontSize: 10,
                              color: meta.color,
                              fontWeight: FontWeight.w600,
                            )),
                      ),
                      const SizedBox(width: 6),
                      Text(timeStr,
                          style: const TextStyle(
                            fontSize: 10.5,
                            color: Colors.grey,
                          )),
                      const Spacer(),
                      if (!resolving)
                        Text('Tap to resolve →',
                            style: TextStyle(
                              fontSize: 10,
                              color: meta.color,
                              fontWeight: FontWeight.w600,
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

  // ── Empty state ───────────────────────────────────────────────────────────
  Widget _buildEmpty() {
    return const Padding(
      padding: EdgeInsets.symmetric(vertical: 30),
      child: Center(
        child: Column(
          children: [
            Icon(Icons.notifications_off_outlined,
                size: 40, color: Colors.grey),
            SizedBox(height: 8),
            Text('No active alerts',
                style: TextStyle(
                    color: Colors.grey, fontSize: 13)),
          ],
        ),
      ),
    );
  }

  // ── District picker ───────────────────────────────────────────────────────
  void _showDistrictPicker() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (_) => Container(
        height: MediaQuery.of(context).size.height * 0.55,
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E1E1E) : Colors.white,
          borderRadius: const BorderRadius.vertical(
              top: Radius.circular(24)),
        ),
        child: Column(
          children: [
            Container(
              margin: const EdgeInsets.only(top: 12),
              width: 40, height: 4,
              decoration: BoxDecoration(
                color: Colors.grey[300],
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
              child: Row(
                children: [
                  const Icon(Icons.location_on,
                      color: Color(0xFF0B1B66), size: 20),
                  const SizedBox(width: 8),
                  Text('Select District',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: isDark
                            ? Colors.white
                            : const Color(0xFF0B1B66),
                      )),
                ],
              ),
            ),
            const Divider(height: 0, thickness: 0.5),
            Expanded(
              child: ListView.builder(
                itemCount: _sriLankaDistricts.length,
                itemBuilder: (ctx, i) {
                  final d          = _sriLankaDistricts[i];
                  final isSelected = d == _selectedDistrict;
                  return InkWell(
                    onTap: () {
                      setState(() => _selectedDistrict = d);
                      Navigator.pop(ctx);
                    },
                    child: Container(
                      color: isSelected
                          ? const Color(0xFF0B1B66).withOpacity(0.07)
                          : null,
                      padding: const EdgeInsets.symmetric(
                          horizontal: 20, vertical: 14),
                      child: Row(
                        children: [
                          Icon(Icons.location_city,
                              size: 18,
                              color: isSelected
                                  ? const Color(0xFF0B1B66)
                                  : Colors.grey),
                          const SizedBox(width: 12),
                          Text(d,
                              style: TextStyle(
                                fontSize: 15,
                                fontWeight: isSelected
                                    ? FontWeight.bold
                                    : FontWeight.normal,
                                color: isSelected
                                    ? const Color(0xFF0B1B66)
                                    : (isDark
                                        ? Colors.white
                                        : Colors.black87),
                              )),
                          const Spacer(),
                          if (isSelected)
                            const Icon(Icons.check,
                                color: Color(0xFF0B1B66), size: 18),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Supporting types ───────────────────────────────────────────────────────

class _NotifMeta {
  final IconData icon;
  final Color    color;
  final String   label;
  const _NotifMeta(this.icon, this.color, this.label);
}