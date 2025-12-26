@echo off
echo ===========================================
echo     TRANSFORMAR PLANILLA MANTIS
echo ===========================================
echo.
echo 1. Buscando archivo "Coordinados..." en carpeta backend...
echo 2. Generando planilla_planificacion_v2.xlsx...
echo.

cd backend
..\venv\Scripts\python.exe process_mantis.py

echo.
echo Proceso finalizado.
echo El archivo Excel deberia abrirse automaticamente.
echo Rellena TECNICO y FECHA, guarda y cierra.
echo.
pause
