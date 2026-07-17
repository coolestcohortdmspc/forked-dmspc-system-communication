from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from ngRadar_Website.views import views



urlpatterns = [
    path('', views.login_view), 
    path('login/', views.login_view, name='login'),
    path('admin/', admin.site.urls),
    path('', include('ngRadar_Website.urls')),

    # built-in auth views: login, logout, password change/reset, etc.
    # provides url names 'login' and 'logout' and use templates under registration 
    # path('accounts/', include('django.contrib.auth.urls')),
]


# FOR PROTOTYPE ONLY: Allows browser to access the local /media/ folder images
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

