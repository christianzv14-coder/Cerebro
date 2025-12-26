@echo off
echo ===========================================
echo       REINICIO TOTAL (APP + BACKEND)
echo ===========================================
echo.
echo 1. Reiniciando Base de Datos (Limpieza Total)...
cd backend
call ..\venv\Scripts\python.exe -c "from app.database import SessionLocal; from app.models.models import Activity, DaySignature; db=SessionLocal(); db.query(Activity).delete(); db.query(DaySignature).delete(); db.commit(); db.close(); print('Base de datos LIMPIA')"
call ..\venv\Scripts\python.exe init_data.py
cd ..
echo.
echo 2. Intentando desinstalacion limpia (opcional)...
adb uninstall com.example.mobile_app >nul 2>&1
if %errorlevel% neq 0 echo [INFO] ADB no encontrado o no disponible, continuando...
echo.
echo 3. Limpiando cache de Flutter...
cd mobile_app
call flutter clean
echo.
echo 3. Obteniendo dependencias...
call flutter pub get
echo.
echo 4. Lanzando App en Emulador...
echo (Instalando version V3-RESTORED con correcciones)
call flutter run -d emulator-5554
pause
