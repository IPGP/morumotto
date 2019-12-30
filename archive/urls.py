# -*- coding: utf-8 -*-
from django.urls import path
from . import views

urlpatterns = [
    path('update', views.update_view, name='index.update'),
    path('stack', views.stack_view, name='index.stack_view'),
    path('newrequest', views.newrequest, name='index.newrequest'),
]
