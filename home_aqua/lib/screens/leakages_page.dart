import 'package:flutter/material.dart';
import '../widgets/leakage_card.dart';
import '../widgets/bell_button.dart';

class LeakagesPage extends StatelessWidget {
  const LeakagesPage({super.key});

  @override
  Widget build(BuildContext context) {

    // ── TEST DATA ──
    // When backend ready, replace with real FastAPI data
    // Kitchen: inFlow=23.1, outFlow=15.7 → diff=7.4 >= 0.1 → LEAK! → RED
    const List<PipelineZone> zones = [
      PipelineZone(
        name: 'Kitchen',
        inFlow: 23.1,   // IN sensor
        outFlow: 15.7,  // OUT sensor
        isValveOpen: true,
        // diff = 23.1 - 15.7 = 7.4 >= 0.1 → leak detected! RED ✅
      ),
      // Parts 2 and 3 will be added here (Washroom, Outdoor)
    ];

    return SafeArea(
      child: Stack(
        children: [

          // ── SCROLLABLE CONTENT ──
          SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
            child: Column(
              children: [

                // ── Build one LeakageCard per zone ──
                ...zones.map((zone) {
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: LeakageCard(
                      zone: zone,
                      onValveToggle: (isOpen) {
                        // TODO: When backend ready:
                        // Call FastAPI to open/close ESP32 valve
                        // e.g. http.post('/valve/${zone.name}', body: {'open': isOpen})
                      },
                    ),
                  );
                }),

              ],
            ),
          ),

          // ── BELL BUTTON ──
          Positioned(
            bottom: 16,
            right: 16,
            child: BellButton(hasNotification: true), // true = leak = red dot
          ),

        ],
      ),
    );
  }
}