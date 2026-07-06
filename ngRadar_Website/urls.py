from django.urls import path
from .views import views

urlpatterns = [
    path('index/', views.get_homepage_index, name='index'),

    # Update the Homepage - Have not tested if this works as expected
    path('index/homepage_updates/', views.get_latest_data, name='latest_data_update'),

    path('dashboard/', views.dashboard_view, name='dashboard_home'),
    
    path('dashboard/update/', views.event_table_partial, name='event_table_update'),

    path('dashboard/graph', views.latency_graphing, name='latency_graphing'),

    # visiting this path for the image 
    path('dashboard/image/<int:event_id>/', views.serve_image, name ='serve_image')
]
