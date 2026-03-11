import 'package:flutter/material.dart';
import '../widgets/leakage_card.dart';
import '../widgets/bell_button.dart';

class LeakagesPage extends StatelessWidget {
  final void Function(int tabIndex) onSwitchTab;

  const LeakagesPage({
    super.key,
    required this.onSwitchTab,
  });

  @override
  Widget build(BuildContext context) {

    final isDark = Theme.of(context).brightness == Brightness.dark;

    const List<PipelineZone> zones = [
      PipelineZone(name: 'Kitchen',  inFlow: 23.1, outFlow: 15.7, isValveOpen: true),
      PipelineZone(name: 'Washroom', inFlow: 23.1, outFlow: 23.1, isValveOpen: false, isValveClosed: true),
      PipelineZone(name: 'Outdoor',  inFlow: 23.1, outFlow: 23.1, isValveOpen: true),
    ];

    final List<AppNotification> notifications = [

      ...zones
          .where((z) => (z.inFlow - z.outFlow) >= 0.1 && z.isValveOpen)
          .map((z) => AppNotification(
                title: 'Leak Detected: ${z.name}',
                message:
                    'A water leak has been detected in the ${z.name} pipeline. '
                    'IN: ${z.inFlow.toStringAsFixed(1)} L/min, '
                    'OUT: ${z.outFlow.toStringAsFixed(1)} L/min. '
                    'Please check immediately.',
                type: 'leak',
                time: '5 mins ago',
                targetTabIndex: 1,
              )),

      const AppNotification(
        title: 'Over Limit: Bathroom',
        message:
            'Bathroom consumption reached 140.0L, '
            'exceeding the daily average of 120.0L.',
        type: 'consumption',
        time: 'Just now',
        targetTabIndex: 0,
      ),

    ];

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF121212) : const Color(0xFFEEF4FF),

      body: SafeArea(
        child: Stack(
          children: [

            SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
              child: Column(
                children: [

                  ...zones.map((zone) => Padding(
                        padding: const EdgeInsets.only(bottom: 16),
                        child: LeakageCard(
                          zone: zone,
                          onValveToggle: (isOpen) {},
                        ),
                      )),

                  const _AddDeviceCard(),

                ],
              ),
            ),

            Positioned(
              bottom: 16,
              right: 16,
              child: BellButton(
                hasNotification: notifications.isNotEmpty,
                notifications: notifications,
                onSwitchTab: onSwitchTab,
              ),
            ),

          ],
        ),
      ),
    );
  }
}

class _AddDeviceCard extends StatelessWidget {
  const _AddDeviceCard();

  @override
  Widget build(BuildContext context) {

    final isDark = Theme.of(context).brightness == Brightness.dark;

    return GestureDetector(
      onTap: () {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Device setup coming soon!'),
            backgroundColor: Color(0xFF1A1A6E),
            duration: Duration(seconds: 2),
          ),
        );
      },
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: 16, horizontal: 16),
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF1E1E1E) : const Color(0xFFEEF4FF),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: const Color(0xFF1A1A6E).withOpacity(0.2),
            width: 1.5,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.06),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                color: Color(0xFF1A1A6E),
              ),
              child: const Icon(Icons.add, color: Colors.white, size: 24),
            ),
            const SizedBox(width: 14),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Add a Device',
                    style: TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF1A1A6E),
                    ),
                  ),
                  Text(
                    'Tap to connect a new ESP32 pipeline sensor',
                    style: TextStyle(fontSize: 11, color: Color(0xFF888888)),
                  ),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_ios, color: Color(0xFF1A1A6E), size: 16),
          ],
        ),
      ),
    );
  }
}