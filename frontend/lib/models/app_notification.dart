// lib/models/app_notification.dart
// AquaSense — Notification model
// Maps to the JSON returned by GET /mobile/notifications

class AppNotification {
  final String title;
  final String message;
  final String type;
  final String time;
  final int    targetTabIndex;

  const AppNotification({
    required this.title,
    required this.message,
    required this.type,
    required this.time,
    this.targetTabIndex = 1,
  });

  factory AppNotification.fromJson(Map<String, dynamic> json) {
    return AppNotification(
      title:          json['title']            as String,
      message:        json['message']          as String,
      type:           json['type']             as String,
      time:           json['time']             as String,
      targetTabIndex: json['target_tab_index'] as int? ?? 1,
    );
  }
}
