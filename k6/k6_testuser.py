"""
DO NOT run this script directly. Create a test user first:
In your terminal:
    docker compose exec ngradar_website python manage.py shell -c \
    'from ngRadar_Website.models.models import ObservatoryEvent; print(ObservatoryEvent.objects.exclude(image_key__isnull=True).exclude(image_key="").order_by("-event_time").first().uuid)'
That will output an image uuid, and you need to define your K6_IMAGE_ID var in your .env with that value.
Be sure K6_USERNAME and K6_PASSWORD are also defined in your .env
Now you can run the k6 tests that require authentication, they will use this test user.
Then paste the below script into the shell and run.

Now you can try running ./control.sh smoketest 
"""

from django.contrib.auth import get_user_model

User = get_user_model()

user = User.objects.create_user(
    username="k6-testuser",
    email="k6-test@example.com",
    password="k6-password",
)

print(user.username, user.is_staff, user.is_superuser, user.is_active) # False False True
