import 'package:flutter/material.dart';
import 'dart:math' as math;

// ── Zone model ──────────────────────────────────────────────
class WaterZone {
  final String name;
  final double used;
  final double average;

  const WaterZone({
    required this.name,
    required this.used,
    required this.average,
  });
}

class DailyConsumptionCard extends StatelessWidget {
  final List<WaterZone> zones;

  const DailyConsumptionCard({
    super.key,
    required this.zones,
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

          // ── TITLE ──
          const Text(
            'Daily Consumption',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: Color(0xFF1A1A6E),
            ),
          ),

          const SizedBox(height: 20),

          // ── ZONE CIRCLES (only if zones exist) ──
          if (zones.isNotEmpty)
            ...List.generate(
              (zones.length / 3).ceil(),
              (rowIndex) {
                final rowZones = zones.sublist(
                  rowIndex * 3,
                  math.min(rowIndex * 3 + 3, zones.length),
                );
                return Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: rowZones.map((zone) {
                      return _ZoneCircle(zone: zone);
                    }).toList(),
                  ),
                );
              },
            ),

          // ── ADD A DEVICE CARD (ALWAYS shows at bottom) ──
          // User can always tap this to add a new ESP32 device
          _AddDeviceCard(),

        ],
      ),
    );
  }
}


// ── ADD A DEVICE CARD ─────────────────────────────────────────
// Always visible at the bottom of Daily Consumption card
// When tapped → will connect to backend to register new device
class _AddDeviceCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        // ── TODO: When backend ready ──
        // Navigate to device setup page or
        // call FastAPI to register new ESP32 device
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
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: const Color(0xFF1A1A6E).withValues(alpha: 0.2),
            width: 1.5,
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [

            // ── "+" icon ──
            Container(
              width: 36,
              height: 36,
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                color: Color(0xFF1A1A6E),
              ),
              child: const Icon(
                Icons.add,
                color: Colors.white,
                size: 22,
              ),
            ),

            const SizedBox(width: 12),

            // ── Text ──
            const Column(
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
                  'Tap to connect a new ESP32 sensor',
                  style: TextStyle(
                    fontSize: 11,
                    color: Color(0xFF888888),
                  ),
                ),
              ],
            ),

            const Spacer(),

            // ── Arrow icon ──
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


// ── ZONE CIRCLE ──────────────────────────────────────────────
class _ZoneCircle extends StatelessWidget {
  final WaterZone zone;

  const _ZoneCircle({required this.zone});

  @override
  Widget build(BuildContext context) {
    final bool isOverLimit = zone.used >= zone.average;
    final double progress  = isOverLimit
        ? 1.0
        : (zone.used / zone.average).clamp(0.0, 1.0);
    final Color arcColor   = isOverLimit
        ? const Color(0xFFD80B0B)
        : const Color(0xFF1A1A6E);
    final Color textColor  = isOverLimit
        ? const Color(0xFFD80B0B)
        : const Color(0xFF1A1A6E);

    return Column(
      children: [

        SizedBox(
          width: 95,
          height: 95,
          child: Stack(
            alignment: Alignment.center,
            children: [

              CustomPaint(
                size: const Size(95, 95),
                painter: _ArcPainter(
                  progress: 1.0,
                  color: const Color(0xFFE0E0E0),
                  strokeWidth: 8,
                ),
              ),

              CustomPaint(
                size: const Size(95, 95),
                painter: _ArcPainter(
                  progress: progress,
                  color: arcColor,
                  strokeWidth: 8,
                ),
              ),

              Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    zone.used.toStringAsFixed(1),
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: textColor,
                      height: 1.0,
                    ),
                  ),
                  Text(
                    'Liters',
                    style: TextStyle(
                      fontSize: 10,
                      color: textColor,
                      fontWeight: FontWeight.w400,
                    ),
                  ),
                ],
              ),

            ],
          ),
        ),

        const SizedBox(height: 8),

        Text(
          zone.name,
          style: const TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.bold,
            color: Color(0xFF1A1A6E),
          ),
        ),

        if (isOverLimit)
          const Text(
            'Over limit!',
            style: TextStyle(
              fontSize: 10,
              color: Color(0xFFD80B0B),
              fontWeight: FontWeight.w500,
            ),
          ),

      ],
    );
  }
}


// ── ARC PAINTER ──────────────────────────────────────────────
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
    final double radius  = (size.width - strokeWidth) / 2;

    const double startAngle = 140 * math.pi / 180;
    final double sweepAngle = 260 * math.pi / 180 * progress;

    canvas.drawArc(
      Rect.fromCircle(center: Offset(centerX, centerY), radius: radius),
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