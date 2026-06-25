import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'auth_service.dart'; // Ensure this matches your actual auth service path

class NotificationService {
  // Singleton pattern to ensure we use a unified instance across the app
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FirebaseMessaging _fcm = FirebaseMessaging.instance;

  /// Initializes notification permissions and fetches the current device token
  Future<void> init() async {
    try {
      // Request permissions explicitly
      final settings = await _fcm.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );

      if (settings.authorizationStatus == AuthorizationStatus.authorized ||
          settings.authorizationStatus == AuthorizationStatus.provisional) {
        debugPrint('Notification permissions granted ✓');
        await _registerToken();
      } else {
        debugPrint('Notification permissions denied or restricted ✕');
      }

      // Listen for token rotations while the app is active and automatically push updates
      _fcm.onTokenRefresh.listen((newToken) async {
        debugPrint('FCM Token rotated/refreshed: $newToken');
        await AuthService.updateFcmToken(newToken);
      });

    } catch (e) {
      debugPrint('Error initializing NotificationService: $e');
    }
  }

  /// Private helper to fetch the token and send it safely to the backend
  Future<void> _registerToken() async {
    try {
      final token = await _fcm.getToken();
      if (token != null) {
        debugPrint('\n--- AQUASENSE FCM DEVICE TOKEN ---');
        debugPrint(token);
        debugPrint('-----------------------------------\n');
        
        // Pass this token onto your backend database tracking mapping
        await AuthService.updateFcmToken(token);
      }
    } catch (e) {
      debugPrint('Error fetching FCM device token: $e');
    }
  }
}