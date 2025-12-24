import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/user.dart';
import '../models/activity.dart';

class ApiService {
  // Update this URL for your local or production backend
  // Mobile emulator localhost is 10.0.2.2 usually
  static const String baseUrl = 'http://10.0.2.2:8000/api/v1'; 
  final _storage = const FlutterSecureStorage();

  Future<String?> getToken() async {
    return await _storage.read(key: 'jwt_token');
  }

  Future<User?> login(String email, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: {'username': email, 'password': password},
    );

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      await _storage.write(key: 'jwt_token', value: data['access_token']);
      return await getMe();
    } else {
      throw Exception('Login failed: ${response.body}');
    }
  }

  Future<User> getMe() async {
    final token = await getToken();
    final response = await http.get(
      Uri.parse('$baseUrl/users/me'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      return User.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to get user details');
    }
  }

  Future<List<Activity>> getActivities({DateTime? date}) async {
    final token = await getToken();
    String query = '';
    if (date != null) {
      query = '?fecha=${date.toIso8601String().split('T')[0]}';
    }
    
    final response = await http.get(
      Uri.parse('$baseUrl/activities/$query'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      final List<dynamic> data = json.decode(response.body);
      return data.map((json) => Activity.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load activities');
    }
  }

  Future<Activity> startActivity(String ticketId) async {
    final token = await getToken();
    final response = await http.post(
      Uri.parse('$baseUrl/activities/$ticketId/start'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json'
      },
      body: json.encode({'timestamp': DateTime.now().toIso8601String()}),
    );

    if (response.statusCode == 200) {
      return Activity.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to start activity');
    }
  }
  
  Future<Activity> finishActivity(String ticketId, String resultado, String? motivo, String? obs) async {
    final token = await getToken();
    final response = await http.post(
      Uri.parse('$baseUrl/activities/$ticketId/finish'),
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json'
      },
      body: json.encode({
        'timestamp': DateTime.now().toIso8601String(),
        'resultado': resultado,
        'motivo': motivo,
        'observacion': obs
      }),
    );

    if (response.statusCode == 200) {
      return Activity.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to finish activity: ${response.body}');
    }
  }
}
