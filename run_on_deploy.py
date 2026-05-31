import os
import sys
import subprocess
import glob

print("Running deployment tasks...")


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")

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

user_count = None
try:
    user_count = int(result.stdout.strip().splitlines()[-1])
    if user_count > 0:
        print(f"Database already has {user_count} users, skipping restore...")
    else:
        # Database is empty, restore the latest available backup file.
        backup_files = glob.glob("database_backup_*.json")
        if backup_files:
            backup_file = max(backup_files, key=os.path.getmtime)
            backup_path = os.path.abspath(backup_file)
            print(f"Restoring data from {backup_path}...")
            run_cmd(["python", "manage.py", "loaddata", backup_path], "Data restore failed!")
            print("Data restored successfully!")
        else:
            print("No backup file found, skipping data restore")
except Exception:
    print("Could not check database status, skipping restore...")


# Optional demo data seeding for staging/production demonstrations.
# Disabled by default for safety.
if env_bool("DEMO_SEED_ON_DEPLOY", default=False):
    seed_only_when_empty = env_bool("DEMO_SEED_ONLY_WHEN_EMPTY", default=True)
    should_seed = (user_count == 0) if seed_only_when_empty else True

    if should_seed:
        students_per_course = os.getenv("DEMO_SEED_STUDENTS_PER_COURSE", "2")
        print(
            "DEMO_SEED_ON_DEPLOY enabled. "
            f"Seeding demo data (students per course: {students_per_course})..."
        )
        run_cmd(
            [
                "python",
                "manage.py",
                "seed_demo_data",
                "--students-per-course",
                students_per_course,
            ],
            "Demo data seeding failed!",
        )
        print("Demo data seeded successfully.")
    else:
        print(
            "DEMO_SEED_ON_DEPLOY enabled but skipped because database is not empty "
            "(DEMO_SEED_ONLY_WHEN_EMPTY=true)."
        )

print("Deployment complete!")
