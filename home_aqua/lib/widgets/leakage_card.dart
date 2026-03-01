import 'package:flutter/material.dart';
import 'dart:math' as math;

// ── Leakage Card Model ───────────────────────────────────────
// Represents one pipeline zone (Kitchen, Washroom, Outdoor etc)
// inFlow  = flow sensor at START of pipeline (L/min)
// outFlow = flow sensor at END of pipeline   (L/min)
// isValveOpen = true → valve open (water flowing)
//              false → valve closed (water stopped)
//
// LEAK LOGIC:
//   inFlow - outFlow >= 0.1 → leak detected! → RED card
class PipelineZone {
  final String name;
  final double inFlow;       // L/min from IN sensor
  final double outFlow;      // L/min from OUT sensor
  final bool isValveOpen;    // valve state
  final bool isValveClosed;  // manually closed (yellow state)

  const PipelineZone({
    required this.name,
    required this.inFlow,
    required this.outFlow,
    required this.isValveOpen,
    this.isValveClosed = false,
  });

  // Auto-detect leak: difference >= 0.1 L/min
  bool get hasLeak => (inFlow - outFlow) >= 0.1;
}

// ── Leakage Card Widget ──────────────────────────────────────
// Shows one pipeline zone card with:
//   - Zone name title
//   - "Leak Detected" label when leak exists
//   - IN flow sensor circle (left)
//   - Valve toggle switch (middle)
//   - OUT flow sensor circle (right)
//   - RED border/bg when leak
//   - YELLOW border/bg when valve manually closed
//   - NAVY border/bg when normal
class LeakageCard extends StatefulWidget {
  final PipelineZone zone;

  // Called when user toggles the valve
  // When backend ready: send API call to open/close valve
  final Function(bool isOpen)? onValveToggle;

  const LeakageCard({
    super.key,
    required this.zone,
    this.onValveToggle,
  });

  @override
  State<LeakageCard> createState() => _LeakageCardState();
}

class _LeakageCardState extends State<LeakageCard> {

  // Local valve state (toggles when user taps switch)
  late bool _isValveOpen;

  @override
  void initState() {
    super.initState();
    _isValveOpen = widget.zone.isValveOpen;
  }

  @override
  Widget build(BuildContext context) {
    final bool hasLeak = widget.zone.hasLeak && _isValveOpen;

    // ── CARD COLORS based on state ──
    // RED    = leak detected
    // YELLOW = valve manually closed (no leak, just off)
    // NAVY   = normal, all good
    final Color borderColor = hasLeak
        ? const Color(0xFFD80B0B)       // red — leak!
        : !_isValveOpen
            ? const Color(0xFFE6A817)   // yellow — valve closed
            : const Color(0xFF1A1A6E); // navy — normal

    final Color bgColor = hasLeak
        ? const Color(0xFFD80B0B).withValues(alpha: 0.05)
        : !_isValveOpen
            ? const Color(0xFFE6A817).withValues(alpha: 0.05)
            : Colors.white;

    final Color switchActiveColor = hasLeak
        ? const Color(0xFFD80B0B)
        : !_isValveOpen
            ? const Color(0xFFE6A817)
            : const Color(0xFF2ECC71); // green when open & normal

    return Container(
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: borderColor, width: 2),
        boxShadow: [
          BoxShadow(
            color: borderColor.withValues(alpha: 0.12),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [

          // ── TOP ROW: Leak label + Zone name + warning icon ──
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [

              // Leak Detected label (only shows when leak)
              if (hasLeak)
                const Text(
                  'Leak Detected',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFFD80B0B),
                  ),
                )
              else if (!_isValveOpen)
                const Text(
                  'Valve Closed',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: Color(0xFFE6A817),
                  ),
                )
              else
                const SizedBox(), // empty space when normal

              // Warning icon (only when leak)
              if (hasLeak)
                const Icon(
                  Icons.warning_amber_rounded,
                  color: Color(0xFFD80B0B),
                  size: 20,
                )
              else
                const SizedBox(),

            ],
          ),

          // Zone name (centered)
          Text(
            widget.zone.name,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: borderColor,
            ),
          ),

          const SizedBox(height: 12),

          // ── MAIN ROW: IN circle + Toggle + OUT circle ──
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [

              // ── LEFT: IN flow sensor ──
              _FlowCircle(
                value: widget.zone.inFlow,
                label: 'IN',
                color: borderColor,
              ),

              // ── MIDDLE: Valve toggle switch ──
              Column(
                children: [
                  Transform.scale(
                    scale: 1.3,
                    child: Switch(
                      value: _isValveOpen,
                      onChanged: (value) {
                        setState(() => _isValveOpen = value);
                        // When backend ready:
                        // widget.onValveToggle?.call(value);
                        // Send API call to open/close ESP32 valve
                      },
                      activeColor: switchActiveColor,
                      activeTrackColor: switchActiveColor.withValues(alpha: 0.3),
                      inactiveThumbColor: const Color(0xFFE6A817),
                      inactiveTrackColor:
                          const Color(0xFFE6A817).withValues(alpha: 0.3),
                    ),
                  ),
                ],
              ),

              // ── RIGHT: OUT flow sensor ──
              _FlowCircle(
                value: widget.zone.outFlow,
                label: 'OUT',
                color: borderColor,
              ),

            ],
          ),

        ],
      ),
    );
  }
}


// ── FLOW CIRCLE ──────────────────────────────────────────────
// Circular arc showing L/min value
// Same arc style as Today card and Daily Consumption card
class _FlowCircle extends StatelessWidget {
  final double value; // L/min
  final String label; // "IN" or "OUT"
  final Color color;  // matches card border color

  const _FlowCircle({
    required this.value,
    required this.label,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [

        SizedBox(
          width: 85,
          height: 85,
          child: Stack(
            alignment: Alignment.center,
            children: [

              // Grey background arc
              CustomPaint(
                size: const Size(85, 85),
                painter: _ArcPainter(
                  color: const Color(0xFFE0E0E0),
                  strokeWidth: 7,
                ),
              ),

              // Colored arc (always full — just decorative like screenshot)
              CustomPaint(
                size: const Size(85, 85),
                painter: _ArcPainter(
                  color: color,
                  strokeWidth: 7,
                ),
              ),

              // Value + unit inside
              Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    value.toStringAsFixed(1),
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                      color: color,
                      height: 1.0,
                    ),
                  ),
                  Text(
                    'L/min',
                    style: TextStyle(
                      fontSize: 9,
                      color: color,
                      fontWeight: FontWeight.w400,
                    ),
                  ),
                ],
              ),

            ],
          ),
        ),

        const SizedBox(height: 4),

        // IN / OUT label below circle
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: color,
          ),
        ),

      ],
    );
  }
}


// ── ARC PAINTER ──────────────────────────────────────────────
class _ArcPainter extends CustomPainter {
  final Color color;
  final double strokeWidth;

  _ArcPainter({
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

    // Same arc style as rest of the app
    const double startAngle = 140 * math.pi / 180;
    const double sweepAngle = 260 * math.pi / 180;

    canvas.drawArc(
      Rect.fromCircle(center: Offset(centerX, centerY), radius: radius),
      startAngle,
      sweepAngle,
      false,
      paint,
    );
  }

  @override
  bool shouldRepaint(_ArcPainter oldDelegate) => false;
}