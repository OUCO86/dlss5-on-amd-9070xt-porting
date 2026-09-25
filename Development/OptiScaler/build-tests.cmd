@echo off
setlocal
call "D:\DLSSNR-Lab\build-tools\VC\Auxiliary\Build\vcvarsall.bat" x64
if errorlevel 1 exit /b 1
cd /d D:\DLSSNR-Lab\re9-presr\source
call tools\test-lmxxf-list-split.cmd D:\DLSSNR-Lab\re9-presr\tests
if errorlevel 1 exit /b 1
call tools\test-lmxxf-create-execute.cmd D:\DLSSNR-Lab\re9-presr\tests
if errorlevel 1 exit /b 1
call tools\test-lmxxf-list1-wrap.cmd D:\DLSSNR-Lab\re9-presr\tests
if errorlevel 1 exit /b 1
call tools\test-lmxxf-same-frame-boundary.cmd D:\DLSSNR-Lab\re9-presr\tests
exit /b %errorlevel%
