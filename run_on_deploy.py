import os
import sys
import subprocess
import glob

print("Running deployment tasks...")

def run_cmd(args, error_message):
    result = subprocess.run(args)
    if result.returncode != 0:
        print(error_message)
        sys.exit(1)


# Always run migrations so start.sh deploy flow keeps schema in sync.
print("Applying database migrations...")
run_cmd(["python", "manage.py", "migrate", "--noinput"], "Migration failed!")
print("Migrations completed.")

# Check if database already has data (check User table)
print("Checking if data restore is needed...")
result = subprocess.run(
    ["python", "manage.py", "shell", "-c", 
     "from accounts.models import User; print(User.objects.count())"],
    capture_output=True,
    text=True
)

try:
    user_count = int(result.stdout.strip().splitlines()[-1])
    if user_count > 0:
        print(f"Database already has {user_count} users, skipping restore...")
    else:
        # Database is empty, restore the latest available backup file.
        backup_files = sorted(glob.glob("database_backup_*.json"))
        if backup_files:
            backup_file = backup_files[-1]
            print(f"Restoring data from {backup_file}...")
            run_cmd(["python", "manage.py", "loaddata", backup_file], "Data restore failed!")
            print("Data restored successfully!")
        else:
            print("No backup file found, skipping data restore")
except Exception:
    print("Could not check database status, skipping restore...")

print("Deployment complete!")
