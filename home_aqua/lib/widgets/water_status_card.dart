import 'package:flutter/material.dart';

class WaterStatusCard extends StatelessWidget {
  const WaterStatusCard({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.blue.withValues(alpha: 0.08),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [

          // ── TITLE ──
          const Align(
            alignment: Alignment.centerLeft,
            child: Text(
              'Water Status',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Color(0xFF1A1A6E),
              ),
            ),
          ),

          const SizedBox(height: 16),

          // ── PART 2.2: Circle with text inside ──
          Container(
            width: 110,
            height: 110,
            decoration: BoxDecoration(
              shape: BoxShape.circle,       // perfect circle
              border: Border.all(
                color: const Color(0xFF1A1A6E), // navy blue border
                width: 4,                        // border thickness
              ),
              color: Colors.white,              // white inside
            ),
            child: const Center(
              child: Text(
                // placeholder text for now
                // Part 2.3 will add real value here
                '- -\nL/min',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1A1A6E),
                  height: 1.4,
                ),
              ),
            ),
          ),

          const SizedBox(height: 16),

          // ── BOTTOM TEXT ──
          const Text(
            'Water running',
            style: TextStyle(
              fontSize: 13,
              color: Color(0xFF888888),
            ),
          ),

        ],
      ),
    );
  }
}