// import 'dart:convert';
// import 'package:http/http.dart' as http;

// class DataService {
//   // Replace with your actual FastAPI server IP (e.g., 10.0.2.2 for Android Emulator)
//   final String baseUrl = "http://YOUR_BACKEND_IP:8000";

//   Future<Map<String, dynamic>> fetchUsageData() async {
//     try {
//       final response = await http.get(Uri.parse('$baseUrl/usage/summary'));
//       if (response.statusCode == 200) {
//         return json.decode(response.body);
//       } else {
//         throw Exception('Failed to load data');
//       }
//     } catch (e) {
//       return {"error": e.toString()};
//     }
//   }
// }
