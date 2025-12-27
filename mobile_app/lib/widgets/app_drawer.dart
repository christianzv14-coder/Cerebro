import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../screens/home_screen.dart';
import '../screens/history_screen.dart';
import '../screens/points_screen.dart';

class AppDrawer extends StatelessWidget {
  const AppDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    final user = Provider.of<AuthProvider>(context).user;

    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          UserAccountsDrawerHeader(
            accountName: Text(user?.tecnicoNombre ?? "Técnico"),
            accountEmail: Text(user?.email ?? "usuario@cerebro.com"),
            currentAccountPicture: const CircleAvatar(
              backgroundColor: Colors.white,
              child: Icon(Icons.person, size: 40, color: Colors.blue),
            ),
            decoration: const BoxDecoration(
              color: Colors.blue,
            ),
          ),
          ListTile(
            leading: const Icon(Icons.today),
            title: const Text('Mi Agenda (Hoy)'),
            onTap: () {
              Navigator.pop(context); // Close drawer
              Navigator.pushReplacement(context,
                  MaterialPageRoute(builder: (_) => const HomeScreen()));
            },
          ),
          ListTile(
            leading: const Icon(Icons.history),
            title: const Text('Historial de Tareas'),
            onTap: () {
              Navigator.pop(context);
              Navigator.pushReplacement(context,
                  MaterialPageRoute(builder: (_) => const HistoryScreen()));
            },
          ),
          ListTile(
            leading: const Icon(Icons.star),
            title: const Text('Mis Puntos'),
            onTap: () {
              Navigator.pop(context);
              Navigator.pushReplacement(context,
                  MaterialPageRoute(builder: (_) => const PointsScreen()));
            },
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.logout, color: Colors.red),
            title: const Text('Cerrar Sesión',
                style: TextStyle(color: Colors.red)),
            onTap: () {
              Navigator.pop(context);
              Provider.of<AuthProvider>(context, listen: false).logout();
            },
          ),
        ],
      ),
    );
  }
}
