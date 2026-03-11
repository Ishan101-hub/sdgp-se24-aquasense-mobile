import 'package:flutter/material.dart';

// Data Model for Plumbers
class Plumber {
  final String name;
  final String contact;
  final String experience;

  Plumber(this.name, this.contact, this.experience);
}

class PlumbersScreen extends StatelessWidget {
  const PlumbersScreen({super.key});

  @override
  Widget build(BuildContext context) {
    // AquaSense primary color
    const Color brandBlue = Color(0xFF0A1B6F);

    final List<Plumber> plumbers = [
      Plumber("Aruna Perera", "071-2345678", "10 Years"),
      Plumber("Sunil Shantha", "077-9876543", "5 Years"),
      Plumber("Kasun Silva", "011-2223334", "8 Years"),
      Plumber("Nimal Bandara", "075-5556667", "12 Years"),
      Plumber("Ruwan Kumara", "072-8889990", "3 Years"),
    ];

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFF),
      appBar: AppBar(
        title: const Text(
          "Registered Plumbers",
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: brandBlue,
        foregroundColor: Colors.white,
        elevation: 0,
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.all(20.0),
            child: Text(
              "Available Specialists",
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: brandBlue,
              ),
            ),
          ),

          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              itemCount: plumbers.length,
              itemBuilder: (context, index) {
                return _buildVerticalPlumberCard(plumbers[index], brandBlue);
              },
            ),
          ),

          Padding(
            padding: const EdgeInsets.all(20.0),
            child: SizedBox(
              width: double.infinity,
              height: 55,
              child: ElevatedButton.icon(
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text("Add Plumber feature coming soon!"),
                    ),
                  );
                },
                icon: const Icon(Icons.person_add),
                label: const Text(
                  "ADD NEW PLUMBER",
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: brandBlue,
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // Helper Widget for vertical cards
  Widget _buildVerticalPlumberCard(Plumber plumber, Color brandBlue) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 15),
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        // Removed 'const' here
        color: Colors.white,
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: brandBlue.withOpacity(0.1)),
        boxShadow: [
          BoxShadow(
            color: brandBlue.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          CircleAvatar(
            radius: 30,
            backgroundColor: brandBlue.withOpacity(0.1),
            child: Icon(Icons.person, color: brandBlue, size: 30),
          ),
          const SizedBox(width: 15),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  plumber.name,
                  style: TextStyle(
                    // Removed 'const' here
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                    color: brandBlue,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  plumber.contact,
                  style: TextStyle(color: Colors.grey[600], fontSize: 14),
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    // Removed 'const' here
                    color: brandBlue.withOpacity(0.05),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    plumber.experience,
                    style: TextStyle(
                      // Removed 'const' here
                      color: brandBlue,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.phone_forwarded, color: Colors.green),
            onPressed: () {
              // Placeholder for calling logic
            },
          ),
        ],
      ),
    );
  }
}
 