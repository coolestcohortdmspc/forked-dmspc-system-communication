from django.db import connection, OperationalError, DatabaseError
from django.http import HttpResponse


class DatabaseUnavailableMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        try:
            connection.ensure_connection()

        except (OperationalError, DatabaseError) as e:
            print(f"DATABASE ERROR: {e}")

            return HttpResponse(
                """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Database Unavailable</title>
                </head>
                <body>
                    <h1> Database Unavailable</h1>
                    <p>
                        The database is currently unavailable.
                        Please try again later.
                    </p>
                </body>
                </html>
                """,
                status=503,
                content_type="text/html",
            )

        return self.get_response(request)