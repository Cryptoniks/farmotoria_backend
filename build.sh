#!/usr/bin/env bash
pip install -r requirements.txt
python manage.py collectstatic --noinput

RUN_MIGRATIONS=true
python manage.py migrate

if [ "$CREATE_SUPERUSER" = "true" ]; then
  echo "Создание superuser..."
  python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print("✅ Superuser '$DJANGO_SUPERUSER_USERNAME' создан!")
else:
    print("⚠️ Superuser уже существует")
EOF
fi