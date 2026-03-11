import 'package:flutter/material.dart';
import '../widgets/custom_bottom_nav.dart';
import 'settings_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen>
    with SingleTickerProviderStateMixin {
  int selectedIndex = 0;
  bool _showNotifPanel = false;
  String _selectedDistrict = 'Colombo';

  late AnimationController _animController;
  late Animation<double> _fadeAnim;
  late Animation<Offset> _slideAnim;

  final List<String> _sriLankaDistricts = [
    'Ampara','Anuradhapura','Badulla','Batticaloa','Colombo',
    'Galle','Gampaha','Hambantota','Jaffna','Kalutara',
    'Kandy','Kegalle','Kilinochchi','Kurunegala','Mannar',
    'Matale','Matara','Monaragala','Mullaitivu','Nuwara Eliya',
    'Polonnaruwa','Puttalam','Ratnapura','Trincomalee','Vavuniya',
  ];

  final List<_NotifItem> _notifications = [
    _NotifItem(type: _NotifType.leak,title:'Leak Detected – Kitchen',body:'IN: 23.1 gal/min vs OUT: 15.7 gal/min. Check immediately.',time:'2 min ago',isRead:false),
    _NotifItem(type: _NotifType.alert,title:'High Usage Alert',body:'Daily usage exceeded average by 40%.',time:'18 min ago',isRead:false),
    _NotifItem(type: _NotifType.valve,title:'Valve Closed – Bathroom',body:'Bathroom line auto-closed after leak alert.',time:'1 hr ago',isRead:false),
    _NotifItem(type: _NotifType.report,title:'Monthly Report Ready',body:'January 2025 report: 15,250 Litres total.',time:'3 hrs ago',isRead:true),
    _NotifItem(type: _NotifType.system,title:'System Reconnected',body:'All IoT sensors are back online.',time:'Yesterday',isRead:true),
  ];

  int get _unreadCount => _notifications.where((n) => !n.isRead).length;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(vsync: this,duration: const Duration(milliseconds: 220));
    _fadeAnim = CurvedAnimation(parent: _animController, curve: Curves.easeOut);
    _slideAnim = Tween<Offset>(begin: const Offset(0, -0.08), end: Offset.zero)
        .animate(CurvedAnimation(parent: _animController, curve: Curves.easeOut));
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  void _toggleNotifPanel() {
    setState(() => _showNotifPanel = !_showNotifPanel);
    _showNotifPanel ? _animController.forward() : _animController.reverse();
  }

  void _closePanel() {
    _animController.reverse().then((_) {
      if (mounted) setState(() => _showNotifPanel = false);
    });
  }

  void _markAllRead() {
    setState(() {
      for (final n in _notifications) n.isRead = true;
    });
  }

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
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Column(
          children: [
            Container(
              margin: const EdgeInsets.only(top: 12),
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                  color: Colors.grey[300],
                  borderRadius: BorderRadius.circular(2)),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
              child: Row(children: [
                const Icon(Icons.location_on, color: Color(0xFF0B1B66), size: 20),
                const SizedBox(width: 8),
                Text('Select District',
                    style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: isDark ? Colors.white : const Color(0xFF0B1B66))),
              ]),
            ),
            const Divider(height: 0, thickness: 0.5),
            Expanded(
              child: ListView.builder(
                itemCount: _sriLankaDistricts.length,
                itemBuilder: (ctx, i) {
                  final d = _sriLankaDistricts[i];
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
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                      child: Row(children: [
                        Icon(Icons.location_city,
                            size: 18,
                            color: isSelected ? const Color(0xFF0B1B66) : Colors.grey),
                        const SizedBox(width: 12),
                        Text(d,
                            style: TextStyle(
                                fontSize: 15,
                                fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                                color: isSelected
                                    ? const Color(0xFF0B1B66)
                                    : (isDark ? Colors.white : Colors.black87))),
                        const Spacer(),
                        if (isSelected)
                          const Icon(Icons.check, color: Color(0xFF0B1B66), size: 18),
                      ]),
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

  final List<Widget> pages = [
    const Center(child: Text("Home",style: TextStyle(fontSize: 22))),
    const Center(child: Text("Leakages",style: TextStyle(fontSize: 22))),
    const Center(child: Text("Report",style: TextStyle(fontSize: 22))),
    const Center(child: Text("Service",style: TextStyle(fontSize: 22))),
    const SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF121212) : Colors.white,
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
          if (_showNotifPanel)
            GestureDetector(
              onTap: _closePanel,
              child: Container(color: Colors.black.withOpacity(0.25)),
            ),
          if (_showNotifPanel)
            Positioned(
              bottom: 90,
              right: 14,
              left: 14,
              child: FadeTransition(
                opacity: _fadeAnim,
                child: SlideTransition(
                    position: _slideAnim,
                    child: _buildNotifPanel()),
              ),
            ),
        ],
      ),
      floatingActionButton: Stack(
        clipBehavior: Clip.none,
        children: [
          FloatingActionButton(
            onPressed: _toggleNotifPanel,
            backgroundColor: _showNotifPanel
                ? const Color(0xFF1A3499)
                : const Color(0xFF0B1B66),
            elevation: 8,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            child: Icon(
              _showNotifPanel
                  ? Icons.notifications_active
                  : Icons.notifications_none,
              color: Colors.white,
            ),
          ),
          if (_unreadCount > 0)
            Positioned(
              right: 6,
              top: 6,
              child: Container(
                width: 18,
                height: 18,
                decoration: BoxDecoration(
                  color: Colors.red,
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white, width: 2),
                ),
                child: Center(
                  child: Text(
                    '$_unreadCount',
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 9,
                        fontWeight: FontWeight.bold),
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

  Widget _buildHeader() {
    return Container(
      width: double.infinity,
      color: const Color(0xFF0B1B66),
      padding: const EdgeInsets.fromLTRB(18, 8, 18, 8),
child: Row(
  crossAxisAlignment: CrossAxisAlignment.center,
  children: [
    Padding(
      padding: const EdgeInsets.only(left: 12),
      child: Transform.scale(
        scale: 1.8,
        child: Image.asset(
          'assets/icons/headerLogo.png',
          height: 120,
          fit: BoxFit.contain,
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
            color: Colors.white.withOpacity(0.3),
            width: 1,
          ),
        ),
        child: Row(
          children: [
            const Icon(Icons.location_on, color: Colors.white, size: 15),
            const SizedBox(width: 4),
            Text(
              _selectedDistrict,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
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

  Widget _buildNotifPanel() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final unread = _unreadCount;
    return Material(
      elevation: 16,
      borderRadius: BorderRadius.circular(22),
      shadowColor: Colors.black38,
      child: Container(
        decoration: BoxDecoration(
            color: isDark ? const Color(0xFF1E1E1E) : Colors.white,
            borderRadius: BorderRadius.circular(22)),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
              decoration: const BoxDecoration(
                color: Color(0xFF0B1B66),
                borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
              ),
              child: Row(
                children: [
                  const Icon(Icons.notifications,color: Colors.white,size: 20),
                  const SizedBox(width: 8),
                  const Text('Notifications',
                      style: TextStyle(color: Colors.white,fontWeight: FontWeight.bold,fontSize: 15)),
                  if (unread > 0) ...[
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                      decoration: BoxDecoration(color: Colors.red,borderRadius: BorderRadius.circular(10)),
                      child: Text('$unread',
                          style: const TextStyle(color: Colors.white,fontSize: 11,fontWeight: FontWeight.bold)),
                    ),
                  ],
                  const Spacer(),
                  if (unread > 0)
                    GestureDetector(
                      onTap: _markAllRead,
                      child: const Text('Mark all read',
                          style: TextStyle(color: Colors.white70, fontSize: 12)),
                    ),
                ],
              ),
            ),
            ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 340),
              child: _notifications.isEmpty
                  ? _buildEmpty()
                  : ListView.separated(
                      shrinkWrap: true,
                      padding: const EdgeInsets.symmetric(vertical: 6),
                      itemCount: _notifications.length,
                      separatorBuilder: (_, __) => const Divider(
                          height: 0, thickness: 0.4, indent: 16, endIndent: 16),
                      itemBuilder: (_, i) => _buildNotifTile(_notifications[i]),
                    ),
            ),
            InkWell(
              onTap: _closePanel,
              borderRadius: const BorderRadius.vertical(bottom: Radius.circular(22)),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 12),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF2A2A2A) : Colors.grey[50],
                  borderRadius: const BorderRadius.vertical(bottom: Radius.circular(22)),
                ),
                child: const Text('Close',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: Color(0xFF0B1B66),fontWeight: FontWeight.w600,fontSize: 13)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildNotifTile(_NotifItem item) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final meta = _meta(item.type);
    return InkWell(
      onTap: () => setState(() => item.isRead = true),
      child: Container(
        color: item.isRead ? Colors.transparent : const Color(0xFFF0F3FF),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                  color: meta.color.withOpacity(0.12),
                  shape: BoxShape.circle),
              child: Icon(meta.icon, color: meta.color, size: 19),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(item.title,
                            style: TextStyle(
                                fontSize: 13,
                                fontWeight: item.isRead ? FontWeight.w500 : FontWeight.bold,
                                color: isDark ? Colors.white : const Color(0xFF0A1B6F))),
                      ),
                      if (!item.isRead)
                        Container(
                          width: 7,
                          height: 7,
                          decoration: const BoxDecoration(
                              color: Colors.red, shape: BoxShape.circle),
                        ),
                    ],
                  ),
                  const SizedBox(height: 2),
                  Text(item.body,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                          fontSize: 11.5,
                          color: Colors.grey[600],
                          height: 1.4)),
                  const SizedBox(height: 3),
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: meta.color.withOpacity(0.10),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(meta.label,
                            style: TextStyle(
                                fontSize: 10,
                                color: meta.color,
                                fontWeight: FontWeight.w600)),
                      ),
                      const SizedBox(width: 6),
                      Text(item.time,
                          style: const TextStyle(fontSize: 10.5, color: Colors.grey)),
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

  Widget _buildEmpty() {
    return const Padding(
      padding: EdgeInsets.symmetric(vertical: 30),
      child: Center(
        child: Column(
          children: [
            Icon(Icons.notifications_off_outlined,size: 40,color: Colors.grey),
            SizedBox(height: 8),
            Text('No notifications',
                style: TextStyle(color: Colors.grey, fontSize: 13)),
          ],
        ),
      ),
    );
  }

  _NotifMeta _meta(_NotifType type) {
    switch (type) {
      case _NotifType.leak:
        return _NotifMeta(Icons.water_damage_outlined, Colors.red, 'Leak');
      case _NotifType.alert:
        return _NotifMeta(Icons.warning_amber_outlined, Colors.orange, 'Alert');
      case _NotifType.valve:
        return _NotifMeta(Icons.settings_input_component_outlined,const Color(0xFF0A1B6F),'Valve');
      case _NotifType.report:
        return _NotifMeta(Icons.bar_chart_outlined, Colors.green, 'Report');
      case _NotifType.system:
        return _NotifMeta(Icons.router_outlined, Colors.blueGrey, 'System');
    }
  }
}

enum _NotifType { leak, alert, valve, report, system }

class _NotifItem {
  final _NotifType type;
  final String title;
  final String body;
  final String time;
  bool isRead;
  _NotifItem({
    required this.type,
    required this.title,
    required this.body,
    required this.time,
    required this.isRead,
  });
}

class _NotifMeta {
  final IconData icon;
  final Color color;
  final String label;
  const _NotifMeta(this.icon, this.color, this.label);
}