# -*- coding: utf-8 -*-
from django.urls import path
from . import views

urlpatterns = [
    path('', views.qc_menu, name='qc_menu'),
    path('status', views.status, name='status'),
    path('update_metadata', views.update_metadata, name='update_metadata'),
    path('check_data', views.check_data, name='check_data'),
    path('map_stations', views.map_stations, name='map_stations'),
    path('check_metadata', views.check_metadata, name='check_metadata'),
    path('metadata_vs_data', views.metadata_vs_data, name='metadata_vs_data'),
    path('plot_completion', views.plot_completion, name='plot_completion'),
    path('plot_response', views.plot_response, name='plot_response'),
]
