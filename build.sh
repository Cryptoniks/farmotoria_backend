#!/usr/bin/env bash
pip install -r requirements.txt
python manage.py collectstatic --noinput || echo "⚠️ Static skipped"

RUN_MIGRATIONS=true
python manage.py migrate

echo "🔍 CREATE_SUPERUSER='$CREATE_SUPERUSER'"
echo "🔍 USERNAME='$DJANGO_SUPERUSER_USERNAME'"

# ✅ Фикс heredoc: отдельный файл
if [ "$CREATE_SUPERUSER" = "true" ] || [ "$CREATE_SUPERUSER" = "True" ]; then
  echo "🚀 Создаём superuser..."
  cat > /tmp/superuser.py << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
username = '$DJANGO_SUPERUSER_USERNAME'
email = '$DJANGO_SUPERUSER_EMAIL'
password = '$DJANGO_SUPERUSER_PASSWORD'
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f"✅ Superuser '{username}' создан!")
else:
    print(f"⚠️ Superuser '{username}' уже существует")
EOF
  python manage.py shell < /tmp/superuser.py
  rm /tmp/superuser.py
else
  echo "⏭️ CREATE_SUPERUSER=off"
fi