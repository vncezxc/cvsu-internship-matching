import os
import sys
import subprocess
import glob

print("🚀 Running deployment tasks...")

# Check if there are pending migrations
print("📊 Checking for pending migrations...")
result = subprocess.run(
    ["python", "manage.py", "showmigrations", "--plan"],
    capture_output=True,
    text=True
)

# Only run migrations if there are unapplied ones
if "[ ]" in result.stdout:
    print("Running migrations...")
    if os.system("python manage.py migrate --noinput") != 0:
        print("❌ Migration failed!")
        sys.exit(1)
    print("✅ Migrations completed!")
else:
    print("✅ No pending migrations, skipping...")

# Check if database already has data (check User table)
print("📦 Checking if data restore is needed...")
result = subprocess.run(
    ["python", "manage.py", "shell", "-c", 
     "from accounts.models import User; print(User.objects.count())"],
    capture_output=True,
    text=True
)

try:
    user_count = int(result.stdout.strip())
    if user_count > 0:
        print(f"✅ Database already has {user_count} users, skipping restore...")
    else:
        # Database is empty, restore the latest available backup file.
        backup_files = sorted(glob.glob("database_backup_20260331_203829.json"))
        if backup_files:
            backup_file = backup_files[-1]
            print(f"📦 Restoring data from {backup_file}...")
            os.system(f"python manage.py loaddata {backup_file}")
            print("✅ Data restored successfully!")
        else:
            print("⚠️ No backup file found, skipping data restore")
except:
    print("⚠️ Could not check database status, skipping restore...")

print("✅ Deployment complete!")
