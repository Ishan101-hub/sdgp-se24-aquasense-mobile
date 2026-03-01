import 'package:flutter/material.dart';
import '../widgets/leakage_card.dart';
import '../widgets/bell_button.dart';

class LeakagesPage extends StatelessWidget {
  const LeakagesPage({super.key});

  @override
  Widget build(BuildContext context) {

    // ── TEST DATA ──
    // When backend ready, replace with real FastAPI data
    const List<PipelineZone> zones = [

      // ── PART 1: Kitchen ──
      // inFlow - outFlow = 23.1 - 15.7 = 7.4 >= 0.1 → LEAK! → RED
      PipelineZone(
        name: 'Kitchen',
        inFlow: 23.1,
        outFlow: 15.7,
        isValveOpen: true,
      ),

      // ── PART 2: Washroom ──
      // isValveOpen = false → valve manually closed → YELLOW
      // No leak because valve is closed by user
      PipelineZone(
        name: 'Washroom',
        inFlow: 23.1,
        outFlow: 23.1, // equal → no leak
        isValveOpen: false, // ← manually closed → yellow state
        isValveClosed: true,
      ),

    ];

    return SafeArea(
      child: Stack(
        children: [

          SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 100),
            child: Column(
              children: [

                ...zones.map((zone) {
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: LeakageCard(
                      zone: zone,
                      onValveToggle: (isOpen) {
                        // TODO: When backend ready:
                        // http.post('/valve/${zone.name}', body: {'open': isOpen})
                      },
                    ),
                  );
                }),

              ],
            ),
          ),

          // Bell with red dot because Kitchen has leak
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