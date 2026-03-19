import 'package:flutter/material.dart';
import 'dart:math' as math;

// ── PipelineZone model ───────────────────────────────────────
// Updated with isActive and lastSeen fields from backend
class PipelineZone {
  final String name;
  final double inFlow;
  final double outFlow;
  final bool isValveOpen;
  final bool isValveClosed;
  final bool isActive;          // NEW — false = offline device
  final DateTime? lastSeen;     // NEW — when device last sent data

  const PipelineZone({
    required this.name,
    required this.inFlow,
    required this.outFlow,
    required this.isValveOpen,
    this.isValveClosed = false,
    this.isActive      = true,  // default active
    this.lastSeen,
  });

  // ── fromJson: parses backend API response ──
  // GET /mobile/zones?network_id=home_01
  factory PipelineZone.fromJson(Map<String, dynamic> json) {
    return PipelineZone(
      name:         json['name']         as String,
      inFlow:       (json['in_flow']     as num).toDouble(),
      outFlow:      (json['out_flow']    as num).toDouble(),
      isValveOpen:  json['valve_open']   as bool,
      isValveClosed: !(json['valve_open'] as bool),
      isActive:     json['is_active']    as bool? ?? true,
      lastSeen:     json['last_seen'] != null
          ? DateTime.tryParse(json['last_seen'] as String)
          : null,
    );
  }

  // ── Leak logic: difference >= 0.1 L/min ──
  bool get hasLeak => (inFlow - outFlow) >= 0.1;

  // ── Human readable last seen ──
  String get lastSeenText {
    if (lastSeen == null) return 'Never';
    final diff = DateTime.now().difference(lastSeen!);
    if (diff.inSeconds < 60)  return '${diff.inSeconds}s ago';
    if (diff.inMinutes < 60)  return '${diff.inMinutes} min ago';
    if (diff.inHours < 24)    return '${diff.inHours} hr ago';
    return '${diff.inDays} days ago';
  }
}

// ── LeakageCard ──────────────────────────────────────────────
class LeakageCard extends StatefulWidget {
  final PipelineZone zone;
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
  late bool _isValveOpen;

  @override
  void initState() {
    super.initState();
    _isValveOpen = widget.zone.isValveOpen;
  }

  // Update local state when backend data refreshes
  @override
  void didUpdateWidget(LeakageCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.zone.isValveOpen != widget.zone.isValveOpen) {
      _isValveOpen = widget.zone.isValveOpen;
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark   = Theme.of(context).brightness == Brightness.dark;
    final bool isOffline = !widget.zone.isActive;            // NEW
    final bool hasLeak   = widget.zone.hasLeak && _isValveOpen && !isOffline;

    // ── Card colors based on state ──
    // 🔴 Leak    → Red
    // 🟡 Closed  → Yellow
    // ⚫ Offline → Grey
    // 🔵 Normal  → Navy (dark) / Green (dark mode)
    final Color borderColor = isOffline
        ? Colors.grey                               // ⚫ Offline
        : hasLeak
            ? const Color(0xFFD80B0B)               // 🔴 Leak
            : !_isValveOpen
                ? const Color(0xFFE6A817)           // 🟡 Valve closed
                : isDark
                    ? const Color(0xFF1A8C4E)       // 🟢 Normal dark
                    : const Color(0xFF1A1A6E);      // 🔵 Normal light

    final Color bgColor = isOffline
        ? (isDark ? const Color(0xFF2A2A2A) : const Color(0xFFF0F0F0))
        : hasLeak
            ? const Color(0xFFD80B0B).withValues(alpha: isDark ? 0.12 : 0.05)
            : !_isValveOpen
                ? const Color(0xFFE6A817).withValues(alpha: isDark ? 0.10 : 0.05)
                : isDark
                    ? const Color(0xFF1E1E1E)
                    : Colors.white;

    final Color switchActiveColor = isOffline
        ? Colors.grey
        : hasLeak
            ? const Color(0xFFD80B0B)
            : !_isValveOpen
                ? const Color(0xFFE6A817)
                : const Color(0xFF1A8C4E);

    final Color switchActiveTrack = switchActiveColor.withValues(alpha: 0.25);

    final double maxFlow = widget.zone.inFlow > widget.zone.outFlow
        ? widget.zone.inFlow
        : widget.zone.outFlow;

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

          // ── Fixed height top row ──
          SizedBox(
            height: 20,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [

                // Status label
                Text(
                  isOffline
                      ? 'Device Offline'           // ⚫
                      : hasLeak
                          ? 'Leak Detected'         // 🔴
                          : !_isValveOpen
                              ? 'Valve Closed'      // 🟡
                              : '',                 // Normal → empty
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: isOffline
                        ? Colors.grey
                        : hasLeak
                            ? const Color(0xFFD80B0B)
                            : const Color(0xFFE6A817),
                  ),
                ),

                // Warning icon — only for leak
                Opacity(
                  opacity: hasLeak ? 1.0 : 0.0,
                  child: const Icon(
                    Icons.warning_amber_rounded,
                    color: Color(0xFFD80B0B),
                    size: 20,
                  ),
                ),

              ],
            ),
          ),

          // Zone name
          Text(
            widget.zone.name,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: isDark
                  ? (isOffline ? Colors.grey : Colors.white)
                  : borderColor,
            ),
          ),

          // ── Last seen (only for offline devices) ──
          if (isOffline)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                'Last seen: ${widget.zone.lastSeenText}',
                style: const TextStyle(
                  fontSize: 11,
                  color: Colors.grey,
                ),
              ),
            ),

          const SizedBox(height: 12),

          // ── IN circle + Switch + OUT circle ──
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [

              // IN sensor
              _FlowCircle(
                value:    widget.zone.inFlow,
                maxFlow:  maxFlow,
                label:    'IN',
                color:    isOffline ? Colors.grey : (isDark ? Colors.white70 : borderColor),
                arcColor: isOffline ? Colors.grey : borderColor,
                isDark:   isDark,
              ),

              // Valve toggle switch
              // ── DISABLED when offline ──
              Transform.scale(
                scale: 1.3,
                child: Switch(
                  value: _isValveOpen,
                  // onChanged = null → disabled when offline ✅
                  onChanged: isOffline
                      ? null
                      : (value) {
                          setState(() => _isValveOpen = value);
                          widget.onValveToggle?.call(value);
                        },
                  activeColor:        switchActiveColor,
                  activeTrackColor:   switchActiveTrack,
                  inactiveThumbColor: isOffline
                      ? Colors.grey
                      : const Color(0xFFE6A817),
                  inactiveTrackColor: isOffline
                      ? Colors.grey.withValues(alpha: 0.3)
                      : const Color(0xFFE6A817).withValues(alpha: 0.3),
                ),
              ),

              // OUT sensor
              _FlowCircle(
                value:    widget.zone.outFlow,
                maxFlow:  maxFlow,
                label:    'OUT',
                color:    isOffline ? Colors.grey : (isDark ? Colors.white70 : borderColor),
                arcColor: isOffline ? Colors.grey : borderColor,
                isDark:   isDark,
              ),

            ],
          ),

        ],
      ),
    );
  }
}

// ── Flow Circle ───────────────────────────────────────────────
class _FlowCircle extends StatelessWidget {
  final double value;
  final double maxFlow;
  final String label;
  final Color  color;
  final Color  arcColor;
  final bool   isDark;

  const _FlowCircle({
    required this.value,
    required this.maxFlow,
    required this.label,
    required this.color,
    required this.arcColor,
    required this.isDark,
  });

  @override
  Widget build(BuildContext context) {
    final double progress = maxFlow > 0
        ? (value / maxFlow).clamp(0.0, 1.0)
        : 0.0;

    return Column(
      children: [
        SizedBox(
          width: 85,
          height: 85,
          child: Stack(
            alignment: Alignment.center,
            children: [

              CustomPaint(
                size: const Size(85, 85),
                painter: _ArcPainter(
                  progress: 1.0,
                  color: isDark
                      ? const Color(0xFF333333)
                      : const Color(0xFFE0E0E0),
                  strokeWidth: 7,
                ),
              ),

              CustomPaint(
                size: const Size(85, 85),
                painter: _ArcPainter(
                  progress: progress,
                  color: arcColor,
                  strokeWidth: 7,
                ),
              ),

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
                    style: TextStyle(fontSize: 9, color: color),
                  ),
                ],
              ),

            ],
          ),
        ),
        const SizedBox(height: 4),
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

// ── Arc Painter ───────────────────────────────────────────────
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

    canvas.drawArc(
      Rect.fromCircle(
        center: Offset(size.width / 2, size.height / 2),
        radius: (size.width - strokeWidth) / 2,
      ),
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