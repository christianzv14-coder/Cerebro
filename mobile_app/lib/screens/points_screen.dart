import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../services/api_service.dart';
import '../widgets/app_drawer.dart';

class PointsScreen extends StatefulWidget {
  const PointsScreen({super.key});

  @override
  State<PointsScreen> createState() => _PointsScreenState();
}

class _PointsScreenState extends State<PointsScreen> {
  final ApiService _api = ApiService();
  late Future<Map<String, dynamic>?> _infoFuture;

  @override
  void initState() {
    super.initState();
    _infoFuture = _api.fetchMyScores();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mis Puntos'),
        elevation: 0,
        backgroundColor: Colors.blueAccent,
      ),
      drawer: const AppDrawer(),
      body: FutureBuilder<Map<String, dynamic>?>(
        future: _infoFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError || !snapshot.hasData || snapshot.data == null) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.sentiment_dissatisfied,
                      size: 60, color: Colors.grey),
                  const SizedBox(height: 16),
                  const Text('No se pudo cargar la información de puntos.'),
                  TextButton(
                    onPressed: () {
                      setState(() {
                        _infoFuture = _api.fetchMyScores();
                      });
                    },
                    child: const Text('Reintentar'),
                  )
                ],
              ),
            );
          }

          final data = snapshot.data!;
          final totalPoints = data['total_points'] ?? 0;
          final totalMoney = data['total_money'] ?? 0;
          final history = data['history'] as List<dynamic>? ?? [];

          // Format currency
          final currencyFormat = NumberFormat.currency(
              locale: 'es_CL', symbol: '\$', decimalDigits: 0);

          return RefreshIndicator(
            onRefresh: () async {
              setState(() {
                _infoFuture = _api.fetchMyScores();
              });
              await _infoFuture;
            },
            child: SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              child: Column(
                children: [
                  // --- HEADER CARD ---
                  Container(
                    width: double.infinity,
                    decoration: const BoxDecoration(
                      gradient: LinearGradient(
                        colors: [Colors.blueAccent, Colors.lightBlue],
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                      ),
                      borderRadius: BorderRadius.only(
                        bottomLeft: Radius.circular(30),
                        bottomRight: Radius.circular(30),
                      ),
                    ),
                    padding: const EdgeInsets.fromLTRB(20, 10, 20, 30),
                    child: Column(
                      children: [
                        const Text(
                          'Ganancia Estimada',
                          style: TextStyle(color: Colors.white70, fontSize: 16),
                        ),
                        const SizedBox(height: 5),
                        Text(
                          currencyFormat.format(totalMoney),
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 36,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 10),
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 16, vertical: 8),
                          decoration: BoxDecoration(
                            color: Colors.white.withOpacity(0.2),
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(
                            '$totalPoints Puntos',
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.bold,
                              fontSize: 18,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 20),

                  // --- CHART SECTION (Simple Bars) ---
                  if (history.isNotEmpty) ...[
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 20),
                      child: Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          'Últimos Trabajos',
                          style: Theme.of(context)
                              .textTheme
                              .titleLarge
                              ?.copyWith(fontWeight: FontWeight.bold),
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    Container(
                      height: 150,
                      margin: const EdgeInsets.symmetric(horizontal: 16),
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(16),
                        boxShadow: [
                          BoxShadow(
                              color: Colors.black12,
                              blurRadius: 10,
                              offset: const Offset(0, 4)),
                        ],
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: _buildChartBars(history),
                      ),
                    ),
                    const SizedBox(height: 20),
                  ],

                  // --- LIST SECTION ---
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 20),
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        'Historial Detallado',
                        style: Theme.of(context)
                            .textTheme
                            .titleLarge
                            ?.copyWith(fontWeight: FontWeight.bold),
                      ),
                    ),
                  ),
                  const SizedBox(height: 10),

                  if (history.isEmpty)
                    const Padding(
                      padding: EdgeInsets.all(20.0),
                      child: Text("No hay registros aún."),
                    )
                  else
                    ListView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: history.length,
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      itemBuilder: (context, index) {
                        final item = history[index];
                        return Card(
                          margin: const EdgeInsets.only(bottom: 12),
                          elevation: 2,
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(12)),
                          child: ListTile(
                            contentPadding: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 8),
                            leading: CircleAvatar(
                              backgroundColor: Colors.blue.shade50,
                              child: const Icon(Icons.check_circle,
                                  color: Colors.blue),
                            ),
                            title: Text(
                              item['ticket_id'] ?? 'Sin Ticket',
                              style:
                                  const TextStyle(fontWeight: FontWeight.bold),
                            ),
                            subtitle: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('${item['date']}'),
                                if (item['items'] != null &&
                                    item['items'].toString().isNotEmpty)
                                  Text(
                                    item['items'],
                                    style: TextStyle(
                                        fontSize: 11, color: Colors.grey[600]),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                              ],
                            ),
                            trailing: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              crossAxisAlignment: CrossAxisAlignment.end,
                              children: [
                                Text(
                                  currencyFormat.format(item['money']),
                                  style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      color: Colors.green,
                                      fontSize: 14),
                                ),
                                Text(
                                  '${item['points']} pts',
                                  style: const TextStyle(
                                      color: Colors.grey, fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
                  const SizedBox(height: 30),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  List<Widget> _buildChartBars(List<dynamic> history) {
    // Take last 7 items (history is sorted desc, so take first 7 and reverse for chart)
    var recent = history.take(7).toList().reversed.toList();
    if (recent.isEmpty) return [];

    double maxPoints = 0;
    for (var h in recent) {
      if ((h['points'] as num) > maxPoints)
        maxPoints = (h['points'] as num).toDouble();
    }
    if (maxPoints == 0) maxPoints = 1;

    return recent.map((item) {
      final points = (item['points'] as num).toDouble();
      final heightFactor = points / maxPoints; // 0.0 to 1.0

      return Column(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          Container(
            width: 12,
            height: 80 * heightFactor, // Max height 80
            decoration: BoxDecoration(
              color: Colors.blueAccent,
              borderRadius: BorderRadius.circular(6),
            ),
          ),
          const SizedBox(height: 4),
          Text(
            points.toInt().toString(),
            style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold),
          ),
        ],
      );
    }).toList();
  }
}
