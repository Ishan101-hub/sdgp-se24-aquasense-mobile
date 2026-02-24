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
            color: Colors.blue.withOpacity(0.08),
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

          // ── PLACEHOLDER for water drop (Part 2.2 later) ──
          const Text(
            '(Water drop here)',
            style: TextStyle(color: Colors.grey),
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