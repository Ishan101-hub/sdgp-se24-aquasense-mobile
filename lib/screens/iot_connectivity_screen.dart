import 'package:flutter/material.dart';

class IoTConnectivityScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("IoT Connectivity")),
      body: ListView(
        padding: EdgeInsets.all(16),
        children: [
          Text(
            "How to connect your device:",
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          SizedBox(height: 10),
          ListTile(
            leading: Icon(Icons.wifi),
            title: Text("1. Turn on device Wi-Fi mode"),
          ),
          ListTile(
            leading: Icon(Icons.bluetooth),
            title: Text("2. Pair via AquaSense App"),
          ),
          ListTile(
            leading: Icon(Icons.sync),
            title: Text("3. Wait for cloud synchronization"),
          ),
        ],
      ),
    );
  }
}
