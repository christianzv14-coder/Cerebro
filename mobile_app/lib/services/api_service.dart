import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../models/models.dart';

class ApiService {
  // Update this URL for your local or production backend
  static String get baseUrl {
    if (kIsWeb) return 'http://127.0.0.1:8000/api/v1';
    if (Platform.isAndroid) return 'http://10.0.2.2:8000/api/v1';
    return 'http://127.0.0.1:8000/api/v1';
  }

  final _storage = const FlutterSecureStorage();

  Future<String?> getToken() async {
    return await _storage.read(key: 'jwt_token');
  }

  Future<Map<String, String>> _getHeaders({String? contentType}) async {
    final token = await getToken();
    final Map<String, String> headers = {
      if (token != null) 'Authorization': 'Bearer $token',
    };
    if (contentType != null) {
      headers['Content-Type'] = contentType;
    }
    return headers;
  }

  Future<User?> login(String email, String password) async {
    final response = await http.post(
      Uri.parse('$baseUrl/auth/login'),
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: {'username': email, 'password': password},
    );

    if (response.statusCode == 200) {
      final data = json.decode(utf8.decode(response.bodyBytes));
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
      return User.fromJson(json.decode(utf8.decode(response.bodyBytes)));
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
      final List<dynamic> data = json.decode(utf8.decode(response.bodyBytes));
      final list = data.map((json) => Activity.fromJson(json)).toList();
      for (var a in list) {
        debugPrint('API_FETCH: Ticket=${a.ticketId}, Estado=${a.estado}');
      }
      return list;
    } else {
      throw Exception(
          'Failed to load activities: ${response.statusCode} ${response.body}');
    }
  }

  Future<Activity> startActivity(String ticketId) async {
    final encodedId = Uri.encodeComponent(ticketId);
    final response = await http.post(
      Uri.parse('$baseUrl/activities/$encodedId/start'),
      headers: await _getHeaders(contentType: 'application/json'),
      body: jsonEncode({'timestamp': DateTime.now().toIso8601String()}),
    );

    if (response.statusCode == 200) {
      return Activity.fromJson(json.decode(utf8.decode(response.bodyBytes)));
    } else {
      throw Exception(
          'Failed to start activity: ${response.statusCode} ${response.body}');
    }
  }

  Future<Activity> finishActivity(
      String ticketId, String resultado, String? motivo, String? obs) async {
    final encodedId = Uri.encodeComponent(ticketId);
    final response = await http.post(
      Uri.parse('$baseUrl/activities/$encodedId/finish'),
      headers: await _getHeaders(contentType: 'application/json'),
      body: jsonEncode({
        'timestamp': DateTime.now().toIso8601String(),
        'resultado': resultado,
        'motivo': motivo,
        'observacion': obs
      }),
    );

    if (response.statusCode == 200) {
      return Activity.fromJson(json.decode(utf8.decode(response.bodyBytes)));
    } else {
      throw Exception(
          'Failed to finish activity: ${response.statusCode} ${response.body}');
    }
  }

  Future<bool> getSignatureStatus() async {
    final token = await getToken();
    final response = await http.get(
      Uri.parse('$baseUrl/signatures/status'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      return json.decode(utf8.decode(response.bodyBytes))['is_signed'];
    }
    return false;
  }

  Future<void> uploadSignature(Uint8List bytes) async {
    final token = await getToken();
    final uri = Uri.parse('$baseUrl/signatures/');

    debugPrint('DEBUG: [API] Subiendo firma (Base64)...');
    final response = await http.post(
      uri,
      headers: {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      },
      body: json.encode({
        'image_base64': base64Encode(bytes),
      }),
    );

    debugPrint('DEBUG: [API] Status: ${response.statusCode}');
    if (response.statusCode != 200) {
      throw Exception(
          'Firma rechazada (${response.statusCode}): ${response.body}');
    }
  }
}
