import os
from django.core.wsgi import get_wsgi_application

print("Starting WSGI application...")  # 👈 Add this

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dispatch_project.settings')

application = get_wsgi_application()
