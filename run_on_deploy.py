import os

os.system("python manage.py migrate")
os.system("python manage.py loaddata db.json")
