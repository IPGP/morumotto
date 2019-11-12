# -*- coding: utf-8 -*-
from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('init_welcome', views.init_welcome, name='init_welcome'),
    # path('init_networks', views.init_networks, name='init_networks'),
    path('init_nslc', views.init_nslc, name='init_nslc'),
    path('init_source', views.init_source, name='init_source'),
    path('init_config', views.init_config, name='init_config'),
    path('init_monitoring', views.init_monitoring, name='init_monitoring'),
    path('init_qcconfig', views.init_qcconfig, name='init_qcconfig'),
    path('init_finish', views.init_finish, name='init_finish'),
    path('about', views.about, name='about'),
    # path('old', views.index_old, name='index.old')
]
