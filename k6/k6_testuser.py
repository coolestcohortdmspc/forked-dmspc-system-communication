"""
DO NOT run this script directly. To create this test user, first run ./control.sh shell
Then run python manage.py shell
Then paste this script into the shell and run.
Add K6_USERNAME=k6-testuser and K6_PASSWORD=k6-password to .env
Now you can run the k6 tests that require authentication, they will use this test user.
"""

from django.contrib.auth import get_user_model

User = get_user_model()

user = User.objects.create_user(
    username="k6-testuser",
    email="k6-test@example.com",
    password="k6-password",
)

print(user.username, user.is_staff, user.is_superuser, user.is_active) # False False True
