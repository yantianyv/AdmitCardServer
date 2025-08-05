@echo off
REM Delete old build directory if exists
if exist "build" rmdir /s /q "build"

REM Create new build directory
mkdir "build"

REM Build Go project
echo Building Go project...
go build -o "build/main.exe" main.go

REM Copy necessary resources
echo Copying assets...
xcopy /E /Y "assets" "build\assets"
xcopy /E /Y "config" "build\config" 
xcopy /E /Y "fonts" "build\fonts"
xcopy /E /Y "templates" "build\templates"

echo Build completed successfully!
pause
