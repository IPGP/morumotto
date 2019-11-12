# -*- coding: utf-8 -*-
from django.conf import settings

MSG_STYLE_SIMPLE = 'Simple'
MSG_STYLE_FULL = 'Full'

DJANGO_DB_LOGGER_ADMIN_LIST_PER_PAGE = getattr(settings, 'DJANGO_DB_LOGGER_ADMIN_LIST_PER_PAGE', 10)

DJANGO_DB_LOGGER_ENABLE_FORMATTER = getattr(settings, 'DJANGO_DB_LOGGER_ENABLE_FORMATTER', False)
