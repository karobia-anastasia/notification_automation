import win32serviceutil
import win32service
import win32event
import servicemanager
import subprocess
import os
import sys

class DjangoService(win32serviceutil.ServiceFramework):
    _svc_name_ = "DjangoWaitressService"
    _svc_display_name_ = "Django Waitress Server Service"
    _svc_description_ = "Runs Django with Waitress as a Windows service."

    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.process:
            self.process.terminate()
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        servicemanager.LogInfoMsg("Starting Django + Waitress service...")

        python_exe = sys.executable
        project_dir = r"C:\Users\Anastasia\Desktop\Anastasia\rexe-automation\dispatch_project"
        waitress_cmd = [
            python_exe, "-m", "waitress", "--listen=0.0.0.0:8000",
            "dispatch_project.wsgi:application"
        ]

        self.process = subprocess.Popen(waitress_cmd, cwd=project_dir)
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(DjangoService)
