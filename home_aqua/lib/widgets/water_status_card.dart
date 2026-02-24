import 'package:flutter/material.dart';

class WaterStatusCard extends StatelessWidget {
  // Test value for now
  // When backend is ready, replace this with real value
  final double flowRate;

  const WaterStatusCard({
    super.key,
    this.flowRate = 23.1, // test value (L/min)
  });

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

          // ── Circle with 23.1 L/min inside ──
          Container(
            width: 110,
            height: 110,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(
                color: const Color(0xFF1A1A6E),
                width: 4,
              ),
              color: Colors.white,
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [

                // ── PART 2.3: Real flow rate value ──
                // Big number (23.1)
                Text(
                  flowRate.toStringAsFixed(1),
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF1A1A6E),
                    height: 1.0,
                  ),
                ),

                const SizedBox(height: 2),

                // Small "L/min" text below number
                const Text(
                  'L/min',
                  style: TextStyle(
                    fontSize: 12,
                    color: Color(0xFF1A1A6E),
                    fontWeight: FontWeight.w400,
                  ),
                ),

              ],
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