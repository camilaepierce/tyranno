#!/usr/bin/env python
"""
Django development server runner.
Listens on 0.0.0.0 with configurable PORT (default 4000).
"""
import os
import sys
import django

# Add archaeo directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'archaeo'))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pteryx.settings')

# Setup Django
django.setup()

# Get port from environment variable or default to 4000
port = os.environ.get('PORT', '4000')
host = '0.0.0.0'

# Import and run the development server
from django.core.management import execute_from_command_line

print(f'Starting Django app on {host}:{port}')

# Run the server
execute_from_command_line([
    'manage.py',
    'runserver',
    f'{host}:{port}'
])
