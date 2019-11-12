# -*- coding: utf-8 -*-
"""siqaco URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.conf import settings
from django.conf.urls import url
from home import views as home_views
from . import celery
import object_tools

urlpatterns = [
    path('admin/', admin.site.urls), # URL FOR ADMIN PAGE
    path('home/', include('django.contrib.auth.urls')), #URL FOR AUTHENTICATION PAGE
    # path('accounts/login/', admin.site.urls),
    path('', home_views.go_to_home, name='home'),
    path('home/', include('home.urls')),
    # path('login/', home_views.login, name="login"),
    # path('logout/', home_views.logout, name="logout"),
    path('seismicarchive/',include('seismicarchive.urls')),
    path('monitoring/',include('monitoring.urls')),
    path('qualitycontrol/',include('qualitycontrol.urls')),
    path('celery_progress/', include('celery_progress.urls')),  # the endpoint is configurable
    # url(r'^celery-progress/', include('celery_progress.urls')),
    path('flower', home_views.flower_redirect, name='flower_redirect'),
    path('rtfm', home_views.documentation_redirect, name='documentation_redirect'),
    path('object-tools/', object_tools.tools.urls),
]

admin.site.site_header = settings.ADMIN_SITE_HEADER
admin.site.index_title = settings.ADMIN_INDEX_TITLE
admin.site.site_title = settings.ADMIN_SITE_TITLE
