#!/usr/bin/env bash
# install dependencies
pip install -r requirements.txt

# collect static files
python manage.py collectstatic --noinput

RUN_MIGRATIONS=true
# run migrations
python manage.py migrate

# create superuser (только первый раз)
if [ "$CREATE_SUPERUSER" = "true" ]; then
  echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')" | python manage.py shell
fi