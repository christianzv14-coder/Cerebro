import 'package:flutter/material.dart';
import '../widgets/app_drawer.dart';

class PointsScreen extends StatelessWidget {
  const PointsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mis Puntos')),
      drawer: const AppDrawer(),
      body: const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.star_border, size: 100, color: Colors.amber),
            SizedBox(height: 20),
            Text(
              'Próximamente',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 10),
            Text('Aquí podrás ver tus puntos acumulados.'),
          ],
        ),
      ),
    );
  }
}
