import 'package:flutter/material.dart';
import '../widgets/leakage_card.dart';
import '../widgets/bell_button.dart';

class LeakagesPage extends StatelessWidget {
  const LeakagesPage({super.key});

  @override
  Widget build(BuildContext context) {

    // ── TEST DATA ──
    const List<PipelineZone> zones = [

      // Kitchen → RED (leak)
      PipelineZone(
        name: 'Kitchen',
        inFlow: 23.1,
        outFlow: 15.7,
        isValveOpen: true,
      ),

      // Washroom → YELLOW (valve closed)
      PipelineZone(
        name: 'Washroom',
        inFlow: 23.1,
        outFlow: 23.1,
        isValveOpen: false,
        isValveClosed: true,
      ),

      // Outdoor → NAVY (normal)
      PipelineZone(
        name: 'Outdoor',
        inFlow: 23.1,
        outFlow: 23.1,
        isValveOpen: true,
      ),

    ];

    return SafeArea(
      child: Stack(
        children: [

          SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
            child: Column(
              children: [

                // ── Zone cards ──
                ...zones.map((zone) {
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: LeakageCard(
                      zone: zone,
                      onValveToggle: (isOpen) {
                        // TODO: http.post('/valve/${zone.name}', body: {'open': isOpen})
                      },
                    ),
                  );
                }),

                // ── PART 4: Add a Device card ──
                const _AddDeviceCard(),

              ],
            ),
          ),

          // Bell with red dot (Kitchen has leak)
          Positioned(
            bottom: 16,
            right: 16,
            child: BellButton(hasNotification: true),
          ),

        ],
      ),
    );
  }
}


// ── ADD A DEVICE CARD ─────────────────────────────────────────
// Always visible at the bottom
// User taps to connect a new ESP32 pipeline device
class _AddDeviceCard extends StatelessWidget {
  const _AddDeviceCard();

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        // TODO: When backend ready →
        // Navigate to device setup page
        // or call FastAPI to register new ESP32 device
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
          color: const Color(0xFFEEF4FF),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: const Color(0xFF1A1A6E).withValues(alpha: 0.2),
            width: 1.5,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.blue.withValues(alpha: 0.06),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [

            // ── "+" circle ──
            Container(
              width: 40,
              height: 40,
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                color: Color(0xFF1A1A6E),
              ),
              child: const Icon(
                Icons.add,
                color: Colors.white,
                size: 24,
              ),
            ),

            const SizedBox(width: 14),

            // ── Text ──
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
                    style: TextStyle(
                      fontSize: 11,
                      color: Color(0xFF888888),
                    ),
                  ),
                ],
              ),
            ),

            // ── Arrow ──
            const Icon(
              Icons.arrow_forward_ios,
              color: Color(0xFF1A1A6E),
              size: 16,
            ),

          ],
        ),
      ),
    );
  }
}