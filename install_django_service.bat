@echo off
echo Installing Django Waitress Windows Service...
cd /d "C:\Users\Anastasia\Desktop\Anastasia\rexe-automation\dispatch_project"
python django_service.py install

echo Starting Django Waitress Service...
python django_service.py start

echo Setting the service to start automatically...
sc config DjangoWaitressService start= auto

echo Done.
pause
