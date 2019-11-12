# -*- coding: utf-8 -*-
from django.urls import path
from . import views

urlpatterns = [
    # path('netgaps', views.index_netgaps, name='index.net_gaps'),
    path('netgaps', views.netgaps, name='net_gaps'),
    path('', views.netgaps, name='net_gaps'),
    path('gaps', views.default_gaps, name='default_gaps'),
    path('overlaps', views.default_overlaps, name='default_overlaps'),
    path('gaps/<str:network_id>/<str:station_id>/<str:location_id>/<str:comp_id>', views.gaps, name='gaps'),
    path('stats/<str:network_id>/<str:station_id>/<str:location_id>/<str:chan_id>', views.stats, name='stats'),
    path('plot/<int:year_id>/<str:filename_id>', views.plot, name='plot'),
    path('netoverlaps', views.netoverlaps, name='net_overlaps'),
    path('overlaps/<str:network_id>/<str:station_id>/<str:location_id>/<str:comp_id>', views.overlaps, name='overlaps'),
    path('update_stats', views.update_stats, name='update_stats'),
    path('availability/<str:network_id>/<str:station_id>/<str:location_id>/<str:comp_id>', views.availability, name='availability'),
    path('availability', views.default_availability, name='availability'),
    path('progress_stats', views.progress_stats, name='progress_stats'),
]
