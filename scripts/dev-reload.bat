@echo off
REM FlyEsports 开发环境重载脚本
echo 正在清理Python缓存并重启后端服务...

cd /d "%~dp0\.."

REM 清理Python缓存
echo 1. 清理Python缓存文件...
for /r backend %%i in (*.pyc) do del "%%i" 2>nul
for /r backend %%i in (__pycache__) do rd /s /q "%%i" 2>nul

REM 重启后端容器以确保代码生效
echo 2. 重启后端容器...
docker-compose restart backend

REM 等待容器启动
echo 3. 等待容器启动...
timeout /t 5 /nobreak > nul

REM 检查健康状态
echo 4. 检查服务状态...
docker ps | findstr backend

echo.
echo ✅ 重载完成！可以测试最新代码了。
echo 💡 如果仍有问题，运行: docker-compose logs backend
pause