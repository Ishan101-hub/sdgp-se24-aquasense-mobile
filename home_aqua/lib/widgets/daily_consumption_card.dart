import 'package:flutter/material.dart';
import 'dart:math' as math;

class DailyConsumptionCard extends StatelessWidget {

  // Test values for now
  // When backend is ready, replace these with real values
  final double kitchenLitres;
  final double bathroomLitres;
  final double outdoorLitres;
  final double maxLitres; // full circle = this value

  const DailyConsumptionCard({
    super.key,
    this.kitchenLitres  = 30,  // test value
    this.bathroomLitres = 140, // test value
    this.outdoorLitres  = 50,  // test value
    this.maxLitres      = 150, // full circle = 150 litres
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
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

          // ── TITLE (centered like screenshot) ──
          const Text(
            'Daily Consumption',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Color(0xFF1A1A6E),
            ),
          ),

          const SizedBox(height: 20),

          // ── 3 CIRCULAR BARS side by side ──
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [

              // Kitchen circle
              _CircleBar(
                litres: kitchenLitres,
                maxLitres: maxLitres,
                label: 'Kitchen',
              ),

              // Bathroom circle
              _CircleBar(
                litres: bathroomLitres,
                maxLitres: maxLitres,
                label: 'Bathroom',
              ),

              // Outdoor circle
              _CircleBar(
                litres: outdoorLitres,
                maxLitres: maxLitres,
                label: 'Outdoor',
              ),

            ],
          ),

          const SizedBox(height: 8),

        ],
      ),
    );
  }
}


// ── SINGLE CIRCLE BAR WIDGET ─────────────────────────────────
// Draws one circular progress bar with litres inside
// and label below — exactly like the screenshot
class _CircleBar extends StatelessWidget {
  final double litres;
  final double maxLitres;
  final String label;

  const _CircleBar({
    required this.litres,
    required this.maxLitres,
    required this.label,
  });

  @override
  Widget build(BuildContext context) {
    double progress = (litres / maxLitres).clamp(0.0, 1.0);

    return Column(
      children: [

        // ── CIRCLE with number inside ──
        SizedBox(
          width: 90,
          height: 90,
          child: Stack(
            alignment: Alignment.center,
            children: [

              // Grey background arc
              SizedBox(
                width: 90,
                height: 90,
                child: CustomPaint(
                  painter: _ArcPainter(
                    progress: 1.0,
                    color: const Color(0xFFE0E0E0), // grey
                    strokeWidth: 8,
                  ),
                ),
              ),

              // Navy blue progress arc
              SizedBox(
                width: 90,
                height: 90,
                child: CustomPaint(
                  painter: _ArcPainter(
                    progress: progress,
                    color: const Color(0xFF1A1A6E), // navy blue
                    strokeWidth: 8,
                  ),
                ),
              ),

              // Number + Liters text inside circle
              Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [

                  // Big number
                  Text(
                    '${litres.toInt()}',
                    style: const TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Color(0xFF1A1A6E),
                      height: 1.0,
                    ),
                  ),

                  // Small "Liters" text
                  const Text(
                    'Liters',
                    style: TextStyle(
                      fontSize: 10,
                      color: Color(0xFF1A1A6E),
                      fontWeight: FontWeight.w400,
                    ),
                  ),

                ],
              ),

            ],
          ),
        ),

        const SizedBox(height: 8),

        // ── LABEL below circle (Kitchen / Bathroom / Outdoor) ──
        Text(
          label,
          style: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.bold,
            color: Color(0xFF1A1A6E),
          ),
        ),

      ],
    );
  }
}


// ── ARC PAINTER ──────────────────────────────────────────────
// Same arc style as TodayCard — open gap at bottom
class _ArcPainter extends CustomPainter {
  final double progress;
  final Color color;
  final double strokeWidth;

  _ArcPainter({
    required this.progress,
    required this.color,
    required this.strokeWidth,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint = Paint()
      ..color = color
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final double centerX = size.width / 2;
    final double centerY = size.height / 2;
    final double radius = (size.width - strokeWidth) / 2;

    // Same arc angles as TodayCard for consistency
    const double startAngle = 140 * math.pi / 180;
    final double sweepAngle = 260 * math.pi / 180 * progress;

    canvas.drawArc(
      Rect.fromCircle(
        center: Offset(centerX, centerY),
        radius: radius,
      ),
      startAngle,
      sweepAngle,
      false,
      paint,
    );
  }

  @override
  bool shouldRepaint(_ArcPainter oldDelegate) {
    return oldDelegate.progress != progress ||
           oldDelegate.color != color;
  }
}