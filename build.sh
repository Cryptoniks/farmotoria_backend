#!/usr/bin/env bash
# Install dependencies
pip install -r requirements.txt

# Collect static files
rm -rf staticfiles/
python manage.py collectstatic --noinput --clear --verbosity=1

# Run migrations
RUN_MIGRATIONS=true
python manage.py migrate

if [ "$CREATE_SUPERUSER" = "true" ]; then
  python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
username = '$DJANGO_SUPERUSER_USERNAME'
email = '$DJANGO_SUPERUSER_EMAIL'
password = '$DJANGO_SUPERUSER_PASSWORD'
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
EOF
fi