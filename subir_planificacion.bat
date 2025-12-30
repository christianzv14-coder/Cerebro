@echo off
cd backend
if "%~1"=="" (
    echo [MODO AUTOMATICO] Buscando archivo de plantilla...
    if exist "plantilla_planificacion_v2.xlsx" (
        echo Archivo encontrado. Iniciando subida...
        python subir_excel.py "plantilla_planificacion_v2.xlsx"
    ) else (
        echo Error: No se encontro "plantilla_planificacion_v2.xlsx" en la carpeta backend.
        echo Ejecuta primero "transformar_mantis.bat".
    )
) else (
    echo [MODO MANUAL] Iniciando subida de: %~1
    python subir_excel.py "%~1"
)
pause
