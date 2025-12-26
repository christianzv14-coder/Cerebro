@echo off
echo ===========================================
echo     CARGAR PLANIFICACION A CEREBRO
echo ===========================================
echo.
cd backend
echo Buscando archivo: plantilla_planificacion_v2.xlsx...
..\venv\Scripts\python.exe subir_excel.py plantilla_planificacion_v2.xlsx
echo.
echo Proceso finalizado.
pause
