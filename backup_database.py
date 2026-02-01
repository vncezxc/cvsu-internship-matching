"""
Simple database backup script for PostgreSQL
Run this to backup your Render database before it expires
"""
import os
import subprocess
import sys
from datetime import datetime

# Your Render database credentials
POSTGRES_HOST = "dpg-d5vbkvggjchc7396h7dg-a"
POSTGRES_DB = "cvsu_internship_n1ap"
POSTGRES_USER = "cvsu_internship_user"
POSTGRES_PASSWORD = "4g4yZ82vQDbwULfH7ymAAgvA5e7SGkI9"
POSTGRES_PORT = "5432"

# Create backup filename with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = f"database_backup_{timestamp}.json"

print(f"Starting database backup from Render...")
print(f"Backup file: {backup_file}")
print(f"Database: {POSTGRES_HOST}/{POSTGRES_DB}")
print("-" * 50)

# Set environment variables for this process
env = os.environ.copy()
env['POSTGRES_HOST'] = POSTGRES_HOST
env['POSTGRES_DB'] = POSTGRES_DB
env['POSTGRES_USER'] = POSTGRES_USER
env['POSTGRES_PASSWORD'] = POSTGRES_PASSWORD
env['POSTGRES_PORT'] = POSTGRES_PORT
env['DJANGO_DEBUG'] = 'False'  # This ensures SSL is required
env['PYTHONIOENCODING'] = 'utf-8'  # Fix encoding issues on Windows

# Apps to backup (excluding problematic system tables)
APPS_TO_BACKUP = [
    'accounts',
    'internship', 
    'chat',
    'dashboard',
]

try:
    print("Connecting to Render database...")
    print("(This may take a minute...)")
    print("\nBacking up your data apps...")
    
    # Capture output instead of writing directly to avoid encoding issues
    cmd = [sys.executable, "manage.py", "dumpdata"] + APPS_TO_BACKUP + [
        "--indent", "2"
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        check=True,
        encoding='utf-8'
    )
    
    # Write the output with explicit UTF-8 encoding
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(result.stdout)
    
    print(f"\n✓ Backup successful!")
    print(f"✓ File saved: {backup_file}")
    print(f"\nYour data is now safely backed up!")
    print(f"\nBackup includes:")
    for app in APPS_TO_BACKUP:
        print(f"  - {app}")
    print(f"\nTo restore this backup later, run:")
    print(f"  python manage.py loaddata {backup_file}")
    
except subprocess.CalledProcessError as e:
    print(f"\n✗ Error during backup: {e}")
    if e.stderr:
        print(f"Error output: {e.stderr}")
    if e.stdout:
        print(f"Standard output: {e.stdout}")
    sys.exit(1)
except Exception as e:
    print(f"\n✗ Unexpected error: {e}")
    sys.exit(1)
