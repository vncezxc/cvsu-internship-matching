import os
import sys

print("🚀 Running deployment tasks...")

# Run migrations
print("📊 Running migrations...")
if os.system("python manage.py migrate") != 0:
    print("❌ Migration failed!")
    sys.exit(1)

# Restore backup data
backup_file = "database_backup_20260103_104532.json"
if os.path.exists(backup_file):
    print(f"📦 Restoring data from {backup_file}...")
    os.system(f"python manage.py loaddata {backup_file}")
    print("✅ Data restored successfully!")
else:
    print(f"⚠️ No backup file found, skipping data restore")

print("✅ Deployment complete!")
