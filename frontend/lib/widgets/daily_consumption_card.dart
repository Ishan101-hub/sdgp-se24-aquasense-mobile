import 'package:flutter/material.dart';
import 'dart:math' as math;

// ── Zone model ───────────────────────────────────────────────
// name    = zone_name from backend  e.g. "Bathroom 01"
// used    = today's usage in litres e.g. 60.0
// average = 30-day average          e.g. 100.0
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

          // ── DYNAMIC ZONE CIRCLES ──────────────────────────
          // Renders however many zones backend returns
          //
          // 1 zone  → ◔             (1 row of 1)
          // 2 zones → ◔ ◔           (1 row of 2)
          // 3 zones → ◔ ◔ ◔         (1 row of 3)
          // 4 zones → ◔ ◔ ◔         (row 1)
          //           ◔              (row 2)
          // 5 zones → ◔ ◔ ◔         (row 1)
          //           ◔ ◔            (row 2)
          // Works for any number! ✅
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

          // ── ADD A DEVICE CARD (always at bottom) ──
          _AddDeviceCard(),

        ],
      ),
    );
  }
}


// ── ZONE CIRCLE ──────────────────────────────────────────────
// Shows circular arc + litres used + zone name
// Navy  = normal (used < average)
// RED   = over limit (used >= average)
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
    final Color textColor  = arcColor;

    return Column(
      children: [

        // ── Arc circle ──
        SizedBox(
          width: 95,
          height: 95,
          child: Stack(
            alignment: Alignment.center,
            children: [

              // Grey background arc
              CustomPaint(
                size: const Size(95, 95),
                painter: _ArcPainter(
                  progress: 1.0,
                  color: const Color(0xFFE0E0E0),
                  strokeWidth: 8,
                ),
              ),

              // Colored progress arc
              CustomPaint(
                size: const Size(95, 95),
                painter: _ArcPainter(
                  progress: progress,
                  color: arcColor,
                  strokeWidth: 8,
                ),
              ),

              // Litres + label inside circle
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

        // ── Zone name from API ──
        // e.g. "Bathroom 01", "Bathroom 02", "Kitchen 01" ✅
        Text(
          zone.name,
          textAlign: TextAlign.center,
          style: const TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.bold,
            color: Color(0xFF1A1A6E),
          ),
        ),

        // Over limit warning
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


// ── ADD A DEVICE CARD ──────────────────────────────────────
class _AddDeviceCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
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
            Container(
              width: 36,
              height: 36,
              decoration: const BoxDecoration(
                shape: BoxShape.circle,
                color: Color(0xFF1A1A6E),
              ),
              child: const Icon(Icons.add, color: Colors.white, size: 22),
            ),
            const SizedBox(width: 12),
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
                  style: TextStyle(fontSize: 11, color: Color(0xFF888888)),
                ),
              ],
            ),
            const Spacer(),
            const Icon(Icons.arrow_forward_ios, color: Color(0xFF1A1A6E), size: 16),
          ],
        ),
      ),
    );
  }
}


// ── ARC PAINTER ──────────────────────────────────────────────
class _ArcPainter extends CustomPainter {
  final double progress;
  final Color  color;
  final double strokeWidth;

  _ArcPainter({
    required this.progress,
    required this.color,
    required this.strokeWidth,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color       = color
      ..strokeWidth = strokeWidth
      ..style       = PaintingStyle.stroke
      ..strokeCap   = StrokeCap.round;

    final cx     = size.width / 2;
    final cy     = size.height / 2;
    final radius = (size.width - strokeWidth) / 2;

    canvas.drawArc(
      Rect.fromCircle(center: Offset(cx, cy), radius: radius),
      140 * math.pi / 180,
      260 * math.pi / 180 * progress,
      false,
      paint,
    );
  }

  @override
  bool shouldRepaint(_ArcPainter old) =>
      old.progress != progress || old.color != color;
}