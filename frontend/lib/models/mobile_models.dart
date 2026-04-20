// // lib/models/mobile_models.dart
// // AquaSense — strongly-typed models for every /mobile/* endpoint response.
// // Import this file in api_service.dart, home_page.dart, home_screen.dart, etc.

// // ─────────────────────────────────────────────────────────────────────────────
// //  /mobile/zones/daily  →  List<ZoneDaily>
// // ─────────────────────────────────────────────────────────────────────────────

// class ZoneDaily {
//   final String name;
//   final double used;
//   final double average;
//   final String zoneId;
//   final String zoneType;
//   final String floor;

//   const ZoneDaily({
//     required this.name,
//     required this.used,
//     required this.average,
//     required this.zoneId,
//     required this.zoneType,
//     required this.floor,
//   });

//   factory ZoneDaily.fromJson(Map<String, dynamic> j) => ZoneDaily(
//         name:     j['name']      as String,
//         used:     (j['used']     as num).toDouble(),
//         average:  (j['average']  as num).toDouble(),
//         zoneId:   j['zone_id']   as String? ?? '',
//         zoneType: j['zone_type'] as String? ?? '',
//         floor:    j['floor']     as String? ?? '',
//       );
// }


// // ─────────────────────────────────────────────────────────────────────────────
// //  /mobile/flowrate  →  FlowRateData
// // ─────────────────────────────────────────────────────────────────────────────

// class FlowRateData {
//   final double flowRate;
//   final String valveState;
//   final String unit;
//   final String? deviceId;
//   final String? timestamp;

//   const FlowRateData({
//     required this.flowRate,
//     required this.valveState,
//     required this.unit,
//     this.deviceId,
//     this.timestamp,
//   });

//   factory FlowRateData.fromJson(Map<String, dynamic> j) => FlowRateData(
//         flowRate:   (j['flow_rate']  as num).toDouble(),
//         valveState: j['valve_state'] as String? ?? 'unknown',
//         unit:       j['unit']        as String? ?? 'L/min',
//         deviceId:   j['device_id']   as String?,
//         timestamp:  j['timestamp']   as String?,
//       );

//   factory FlowRateData.empty() => const FlowRateData(
//         flowRate:   0.0,
//         valveState: 'unknown',
//         unit:       'L/min',
//       );
// }


// // ─────────────────────────────────────────────────────────────────────────────
// //  /mobile/dashboard/today  →  DashboardToday
// // ─────────────────────────────────────────────────────────────────────────────

// class DashboardToday {
//   final double litresUsed;
//   final double dailyAverage;
//   final double percent;
//   final int    activeLeaks;
//   final String date;

//   const DashboardToday({
//     required this.litresUsed,
//     required this.dailyAverage,
//     required this.percent,
//     required this.activeLeaks,
//     required this.date,
//   });

//   factory DashboardToday.fromJson(Map<String, dynamic> j) => DashboardToday(
//         litresUsed:   (j['litresUsed']   as num).toDouble(),
//         dailyAverage: (j['dailyAverage'] as num).toDouble(),
//         percent:      (j['percent']      as num).toDouble(),
//         activeLeaks:  (j['active_leaks'] as num).toInt(),
//         date:          j['date']          as String,
//       );

//   factory DashboardToday.empty() => DashboardToday(
//         litresUsed:   0.0,
//         dailyAverage: 0.0,
//         percent:      0.0,
//         activeLeaks:  0,
//         date:         DateTime.now().toIso8601String().substring(0, 10),
//       );
// }


// // ─────────────────────────────────────────────────────────────────────────────
// //  /mobile/leakages  →  List<LeakageZone>
// // ─────────────────────────────────────────────────────────────────────────────

// class LeakageZone {
//   final int    zoneId;
//   final String zoneSlug;
//   final String zoneName;
//   final String zoneType;
//   final String floor;
//   final double inFlow;
//   final double outFlow;
//   final String valveState;
//   final bool   leak;
//   final String uiState; // "normal" | "leak_detected" | "valve_closed"

//   const LeakageZone({
//     required this.zoneId,
//     required this.zoneSlug,
//     required this.zoneName,
//     required this.zoneType,
//     required this.floor,
//     required this.inFlow,
//     required this.outFlow,
//     required this.valveState,
//     required this.leak,
//     required this.uiState,
//   });

//   factory LeakageZone.fromJson(Map<String, dynamic> j) => LeakageZone(
//         zoneId:     (j['zone_id']   as num).toInt(),
//         zoneSlug:    j['zone_slug']  as String? ?? '',
//         zoneName:    j['zone_name']  as String,
//         zoneType:    j['zone_type']  as String? ?? '',
//         floor:       j['floor']      as String? ?? '',
//         inFlow:     (j['inFlow']     as num).toDouble(),
//         outFlow:    (j['outFlow']    as num).toDouble(),
//         valveState:  j['valve_state'] as String? ?? 'unknown',
//         leak:        j['leak']        as bool,
//         uiState:     j['ui_state']    as String? ?? 'normal',
//       );
// }


// // ─────────────────────────────────────────────────────────────────────────────
// //  /mobile/valve  (POST body)  →  ValveCommand
// // ─────────────────────────────────────────────────────────────────────────────

// class ValveCommand {
//   final int    zoneId;
//   final String action;   // "open" | "close"
//   final bool   override;

//   const ValveCommand({
//     required this.zoneId,
//     required this.action,
//     this.override = false,
//   });

//   Map<String, dynamic> toJson() => {
//         'zone_id':  zoneId,
//         'action':   action,
//         'override': override,
//       };
// }


// // ─────────────────────────────────────────────────────────────────────────────
// //  /mobile/report/monthly  →  MonthlyReport
// // ─────────────────────────────────────────────────────────────────────────────

// class MonthlyReport {
//   final int    year;
//   final int    month;
//   final double totalUsageL;
//   final double weeklyAvgL;
//   final double dailyAvgL;
//   final int    leaksDetected;
//   final int    daysWithData;

//   const MonthlyReport({
//     required this.year,
//     required this.month,
//     required this.totalUsageL,
//     required this.weeklyAvgL,
//     required this.dailyAvgL,
//     required this.leaksDetected,
//     required this.daysWithData,
//   });

//   factory MonthlyReport.fromJson(Map<String, dynamic> j) => MonthlyReport(
//         year:          (j['year']           as num).toInt(),
//         month:         (j['month']          as num).toInt(),
//         totalUsageL:   (j['total_usage_L']  as num).toDouble(),
//         weeklyAvgL:    (j['weekly_avg_L']   as num).toDouble(),
//         dailyAvgL:     (j['daily_avg_L']    as num).toDouble(),
//         leaksDetected: (j['leaks_detected'] as num).toInt(),
//         daysWithData:  (j['days_with_data'] as num).toInt(),
//       );

//   factory MonthlyReport.empty(int year, int month) => MonthlyReport(
//         year:          year,
//         month:         month,
//         totalUsageL:   0.0,
//         weeklyAvgL:    0.0,
//         dailyAvgL:     0.0,
//         leaksDetected: 0,
//         daysWithData:  0,
//       );
// }


// // ─────────────────────────────────────────────────────────────────────────────
// //  /mobile/alerts  →  AlertsResponse  +  AlertItem
// // ─────────────────────────────────────────────────────────────────────────────

// class AlertItem {
//   final int     id;
//   final String  zoneName;
//   final String  deviceId;
//   final String  eventType;
//   final String? description;
//   final bool    resolved;
//   final String? resolvedAt;
//   final String  timestamp;

//   const AlertItem({
//     required this.id,
//     required this.zoneName,
//     required this.deviceId,
//     required this.eventType,
//     this.description,
//     required this.resolved,
//     this.resolvedAt,
//     required this.timestamp,
//   });

//   factory AlertItem.fromJson(Map<String, dynamic> j) => AlertItem(
//         id:          (j['id']          as num).toInt(),
//         zoneName:     j['zone_name']   as String,
//         deviceId:     j['device_id']   as String,
//         eventType:    j['event_type']  as String,
//         description:  j['description'] as String?,
//         resolved:     j['resolved']    as bool,
//         resolvedAt:   j['resolved_at'] as String?,
//         timestamp:    j['timestamp']   as String,
//       );
// }

// class AlertsResponse {
//   final int             unreadCount;
//   final List<AlertItem> items;

//   const AlertsResponse({required this.unreadCount, required this.items});

//   factory AlertsResponse.fromJson(Map<String, dynamic> j) => AlertsResponse(
//         unreadCount: (j['unread_count'] as num).toInt(),
//         items: (j['items'] as List<dynamic>)
//             .map((e) => AlertItem.fromJson(e as Map<String, dynamic>))
//             .toList(),
//       );

//   factory AlertsResponse.empty() =>
//       const AlertsResponse(unreadCount: 0, items: []);
// }


// // ─────────────────────────────────────────────────────────────────────────────
// //  /mobile/notifications  →  List<MobileNotification>
// // ─────────────────────────────────────────────────────────────────────────────

// class MobileNotification {
//   final String title;
//   final String message;
//   final String type;
//   final String time;
//   final int    targetTabIndex;
//   bool         isRead;

//   MobileNotification({
//     required this.title,
//     required this.message,
//     required this.type,
//     required this.time,
//     required this.targetTabIndex,
//     this.isRead = false,
//   });

//   factory MobileNotification.fromJson(Map<String, dynamic> j) =>
//       MobileNotification(
//         title:          j['title']            as String,
//         message:        j['message']          as String,
//         type:           j['type']             as String,
//         time:           j['time']             as String,
//         targetTabIndex: (j['target_tab_index'] as num).toInt(),
//       );
// }

// lib/models/mobile_models.dart
// AquaSense — strongly-typed models for every /mobile/* endpoint response.

// ─────────────────────────────────────────────────────────────────────────────
//  /mobile/zones/daily  →  List<ZoneDaily>
// ─────────────────────────────────────────────────────────────────────────────

class ZoneDaily {
  final String name;
  final double used;
  final double average;
  final String zoneId;
  final String zoneType;
  final String floor;

  const ZoneDaily({
    required this.name,
    required this.used,
    required this.average,
    required this.zoneId,
    required this.zoneType,
    required this.floor,
  });

  factory ZoneDaily.fromJson(Map<String, dynamic> j) => ZoneDaily(
        name:     j['name']      as String,
        used:     (j['used']     as num).toDouble(),
        average:  (j['average']  as num).toDouble(),
        zoneId:   j['zone_id']   as String? ?? '',
        zoneType: j['zone_type'] as String? ?? '',
        floor:    j['floor']     as String? ?? '',
      );
}


// ─────────────────────────────────────────────────────────────────────────────
//  /mobile/flowrate  →  FlowRateData
// ─────────────────────────────────────────────────────────────────────────────

class FlowRateData {
  final double flowRate;
  final String valveState;
  final String unit;
  final String? deviceId;
  final String? timestamp;

  const FlowRateData({
    required this.flowRate,
    required this.valveState,
    required this.unit,
    this.deviceId,
    this.timestamp,
  });

  factory FlowRateData.fromJson(Map<String, dynamic> j) => FlowRateData(
        flowRate:   (j['flow_rate']  as num).toDouble(),
        valveState: j['valve_state'] as String? ?? 'unknown',
        unit:       j['unit']        as String? ?? 'L/min',
        deviceId:   j['device_id']   as String?,
        timestamp:  j['timestamp']   as String?,
      );

  factory FlowRateData.empty() => const FlowRateData(
        flowRate:   0.0,
        valveState: 'unknown',
        unit:       'L/min',
      );
}


// ─────────────────────────────────────────────────────────────────────────────
//  /mobile/dashboard/today  →  DashboardToday
// ─────────────────────────────────────────────────────────────────────────────

class DashboardToday {
  final double litresUsed;
  final double dailyAverage;
  final double percent;
  final int    activeLeaks;
  final String date;

  const DashboardToday({
    required this.litresUsed,
    required this.dailyAverage,
    required this.percent,
    required this.activeLeaks,
    required this.date,
  });

  factory DashboardToday.fromJson(Map<String, dynamic> j) => DashboardToday(
        litresUsed:   (j['litresUsed']   as num).toDouble(),
        dailyAverage: (j['dailyAverage'] as num).toDouble(),
        percent:      (j['percent']      as num).toDouble(),
        activeLeaks:  (j['active_leaks'] as num).toInt(),
        date:          j['date']          as String,
      );

  factory DashboardToday.empty() => DashboardToday(
        litresUsed:   0.0,
        dailyAverage: 0.0,
        percent:      0.0,
        activeLeaks:  0,
        date:         DateTime.now().toIso8601String().substring(0, 10),
      );
}


// ─────────────────────────────────────────────────────────────────────────────
//  /mobile/leakages  →  List<LeakageZone>
// ─────────────────────────────────────────────────────────────────────────────

class LeakageZone {
  final int    zoneId;
  final String zoneSlug;
  final String zoneName;
  final String zoneType;
  final String floor;
  final double inFlow;
  final double outFlow;
  final String valveState;
  final bool   leak;
  final String uiState;

  const LeakageZone({
    required this.zoneId,
    required this.zoneSlug,
    required this.zoneName,
    required this.zoneType,
    required this.floor,
    required this.inFlow,
    required this.outFlow,
    required this.valveState,
    required this.leak,
    required this.uiState,
  });

  factory LeakageZone.fromJson(Map<String, dynamic> j) => LeakageZone(
        zoneId:     (j['zone_id']   as num).toInt(),
        zoneSlug:    j['zone_slug']  as String? ?? '',
        zoneName:    j['zone_name']  as String,
        zoneType:    j['zone_type']  as String? ?? '',
        floor:       j['floor']      as String? ?? '',
        inFlow:     (j['inFlow']     as num).toDouble(),
        outFlow:    (j['outFlow']    as num).toDouble(),
        valveState:  j['valve_state'] as String? ?? 'unknown',
        leak:        j['leak']        as bool,
        uiState:     j['ui_state']    as String? ?? 'normal',
      );
}


// ─────────────────────────────────────────────────────────────────────────────
//  /mobile/valve  (POST body)  →  ValveCommand
// ─────────────────────────────────────────────────────────────────────────────

class ValveCommand {
  final int    zoneId;
  final String action;
  final bool   override;

  const ValveCommand({
    required this.zoneId,
    required this.action,
    this.override = false,
  });

  Map<String, dynamic> toJson() => {
        'zone_id':  zoneId,
        'action':   action,
        'override': override,
      };
}


// ─────────────────────────────────────────────────────────────────────────────
//  /mobile/report/monthly  →  MonthlyReport
// ─────────────────────────────────────────────────────────────────────────────

class MonthlyReport {
  final int    year;
  final int    month;
  final double totalUsageL;
  final double weeklyAvgL;
  final double dailyAvgL;
  final int    leaksDetected;
  final int    daysWithData;

  const MonthlyReport({
    required this.year,
    required this.month,
    required this.totalUsageL,
    required this.weeklyAvgL,
    required this.dailyAvgL,
    required this.leaksDetected,
    required this.daysWithData,
  });

  factory MonthlyReport.fromJson(Map<String, dynamic> j) => MonthlyReport(
        year:          (j['year']           as num).toInt(),
        month:         (j['month']          as num).toInt(),
        totalUsageL:   (j['total_usage_L']  as num).toDouble(),
        weeklyAvgL:    (j['weekly_avg_L']   as num).toDouble(),
        dailyAvgL:     (j['daily_avg_L']    as num).toDouble(),
        leaksDetected: (j['leaks_detected'] as num).toInt(),
        daysWithData:  (j['days_with_data'] as num).toInt(),
      );

  factory MonthlyReport.empty(int year, int month) => MonthlyReport(
        year:          year,
        month:         month,
        totalUsageL:   0.0,
        weeklyAvgL:    0.0,
        dailyAvgL:     0.0,
        leaksDetected: 0,
        daysWithData:  0,
      );
}


// ─────────────────────────────────────────────────────────────────────────────
//  /mobile/alerts  →  AlertsResponse  +  AlertItem
// ─────────────────────────────────────────────────────────────────────────────

class AlertItem {
  final int     id;
  final String  zoneName;
  final String  deviceId;
  final String  eventType;
  final String? description;
  final bool    resolved;
  final String? resolvedAt;
  final String  timestamp;

  const AlertItem({
    required this.id,
    required this.zoneName,
    required this.deviceId,
    required this.eventType,
    this.description,
    required this.resolved,
    this.resolvedAt,
    required this.timestamp,
  });

  /// All alert types send the user to the Leakages tab (index 1).
  int get targetTabIndex => 1;

  factory AlertItem.fromJson(Map<String, dynamic> j) => AlertItem(
        id:          (j['id']          as num).toInt(),
        zoneName:     j['zone_name']   as String,
        deviceId:     j['device_id']   as String,
        eventType:    j['event_type']  as String,
        description:  j['description'] as String?,
        resolved:     j['resolved']    as bool,
        resolvedAt:   j['resolved_at'] as String?,
        timestamp:    j['timestamp']   as String,
      );
}

class AlertsResponse {
  final int             unreadCount;
  final List<AlertItem> items;

  const AlertsResponse({required this.unreadCount, required this.items});

  factory AlertsResponse.fromJson(Map<String, dynamic> j) => AlertsResponse(
        unreadCount: (j['unread_count'] as num).toInt(),
        items: (j['items'] as List<dynamic>)
            .map((e) => AlertItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  factory AlertsResponse.empty() =>
      const AlertsResponse(unreadCount: 0, items: []);
}


// ─────────────────────────────────────────────────────────────────────────────
//  /mobile/notifications  →  List<MobileNotification>
// ─────────────────────────────────────────────────────────────────────────────

class MobileNotification {
  final String title;
  final String message;
  final String type;
  final String time;
  final int    targetTabIndex;
  bool         isRead;

  MobileNotification({
    required this.title,
    required this.message,
    required this.type,
    required this.time,
    required this.targetTabIndex,
    this.isRead = false,
  });

  factory MobileNotification.fromJson(Map<String, dynamic> j) =>
      MobileNotification(
        title:          j['title']            as String,
        message:        j['message']          as String,
        type:           j['type']             as String,
        time:           j['time']             as String,
        targetTabIndex: (j['target_tab_index'] as num).toInt(),
      );
}