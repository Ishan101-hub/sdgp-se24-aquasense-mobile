import 'package:flutter/material.dart';
import '../widgets/custom_bottom_nav.dart';

class HomeScreen extends StatefulWidget{
  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int selectedIndex = 0;
  final pages = [
    Center(child: Text("Home", style: TextStyle(fontSize: 22))),
    Center(child: Text("Leakages", style: TextStyle(fontSize: 22))),
    Center(child: Text("Report", style: TextStyle(fontSize: 22))),
    Center(child: Text("Service", style: TextStyle(fontSize: 22))),
    Center(child: Text("Settings", style: TextStyle(fontSize: 22))),
  ];

  @override
  Widget build(BuildContext context){
    return Scaffold(
      backgroundColor: Colors.white,
      body: pages[selectedIndex],
      bottomNavigationBar: CustomBottomNav(
        currentIndex: selectedIndex, 
        onTap: (index){
          setState(() {
            selectedIndex = index;
          });
        },
      ),
    );
  }
}