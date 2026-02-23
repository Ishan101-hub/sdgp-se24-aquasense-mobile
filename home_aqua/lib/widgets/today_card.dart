import 'package:flutter/material.dart';
import 'dart:math' as math;

class TodayCard extends StatelessWidget {
  final double dailyAveragePercent;
  final double litresUsed;
  final double dailyAverageLitres; // full average per day (eg: 450 litres)

  const TodayCard({
    super.key,
    this.dailyAveragePercent = 48,    // test value
    this.litresUsed = 220,            // test value
    this.dailyAverageLitres = 450,    // test value (220 is 48% of 450)
  });

  @override
  Widget build(BuildContext context) {
    // Calculate how much of the circle to fill
    // Example: 220 / 450 = 0.48 means 48% filled
    double progress = (litresUsed / dailyAverageLitres).clamp(0.0, 1.0);

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
              'Today',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: Color(0xFF1A1A6E),
              ),
            ),
          ),

          const SizedBox(height: 16),

          // ── PART 1.4: Circular loading bar with 220 Litres inside ──
          SizedBox(
            width: 130,
            height: 130,
            child: Stack(
              // Stack means put things on TOP of each other
              alignment: Alignment.center,
              children: [

                // ── BACKGROUND CIRCLE (grey, always full) ──
                SizedBox(
                  width: 130,
                  height: 130,
                  child: CustomPaint(
                    painter: _CircularBarPainter(
                      progress: 1.0,             // always full circle
                      color: const Color(0xFFE0E0E0), // grey color
                      strokeWidth: 10,
                    ),
                  ),
                ),

                // ── FOREGROUND CIRCLE (navy blue, fills based on litres) ──
                SizedBox(
                  width: 130,
                  height: 130,
                  child: CustomPaint(
                    painter: _CircularBarPainter(
                      progress: progress,            // 0.0 to 1.0
                      color: const Color(0xFF1A1A6E), // navy blue
                      strokeWidth: 10,
                    ),
                  ),
                ),

                // ── TEXT INSIDE CIRCLE (220 Litres) ──
                // PART 1.3 text now sits inside the circle
                RichText(
                  textAlign: TextAlign.center,
                  text: TextSpan(
                    children: [

                      // Big number "220"
                      TextSpan(
                        text: '${litresUsed.toInt()}',
                        style: const TextStyle(
                          fontSize: 36,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF1A1A6E),
                        ),
                      ),

                      // Small word "Litres" on new line
                      const TextSpan(
                        text: '\nLitres',
                        style: TextStyle(
                          fontSize: 13,
                          color: Color(0xFF1A1A6E),
                          fontWeight: FontWeight.w400,
                        ),
                      ),

                    ],
                  ),
                ),

              ],
            ),
          ),

          const SizedBox(height: 16),

          // ── PART 1.2: "48% of daily average" text ──
          Text(
            '${dailyAveragePercent.toInt()}% of daily average',
            style: const TextStyle(
              fontSize: 13,
              color: Color(0xFF888888),
            ),
          ),

        ],
      ),
    );
  }
}


// ── CUSTOM PAINTER: This draws the circular arc ──────────────────
// Think of this like a drawing tool that draws the circle shape
class _CircularBarPainter extends CustomPainter {
  final double progress;   // how much to fill: 0.0 = empty, 1.0 = full
  final Color color;       // what color to draw
  final double strokeWidth; // how thick the circle line is

  _CircularBarPainter({
    required this.progress,
    required this.color,
    required this.strokeWidth,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final Paint paint = Paint()
      ..color = color
      ..strokeWidth = strokeWidth
      ..style = PaintingStyle.stroke  // only draw the outline, not filled
      ..strokeCap = StrokeCap.round;  // rounded ends of the arc

    final double centerX = size.width / 2;
    final double centerY = size.height / 2;
    final double radius = (size.width - strokeWidth) / 2;

    // startAngle: where the arc starts
    // -140 degrees means it starts from bottom left (like your screenshot)
    const double startAngle = 140 * math.pi / 180;

    // sweepAngle: how far the arc goes
    // 260 degrees total sweep (not full circle, open at bottom)
    final double sweepAngle = 260 * math.pi / 180 * progress;

    canvas.drawArc(
      Rect.fromCircle(center: Offset(centerX, centerY), radius: radius),
      startAngle,
      sweepAngle,
      false, // false = do not connect to center (just arc)
      paint,
    );
  }

  @override
  bool shouldRepaint(_CircularBarPainter oldDelegate) {
    // Repaint only if something changed
    return oldDelegate.progress != progress ||
           oldDelegate.color != color;
  }
}