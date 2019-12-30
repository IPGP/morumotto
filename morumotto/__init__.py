# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import os
# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery import app as celery_app
from . import toolbox
# from archive.models import Configuration

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKING_DIR =  os.path.join(BASE_DIR, "WORKING_DIR/")
__all__ = ('celery_app',)

if not os.path.exists(os.path.join(WORKING_DIR,"LOG")):
    os.makedirs(os.path.join(WORKING_DIR,"LOG"))

if not os.path.exists(os.path.join(WORKING_DIR,"PLOT")):
    os.makedirs(os.path.join(WORKING_DIR,"PLOT"))
toolbox.delete_plots() #see docstring of this function for details

if not os.path.exists(os.path.join(WORKING_DIR,"POST")):
    os.makedirs(os.path.join(WORKING_DIR,"POST"))

if not os.path.exists(os.path.join(WORKING_DIR,"PATCH")):
    os.makedirs(os.path.join(WORKING_DIR,"PATCH"))

if not os.path.exists(os.path.join(WORKING_DIR,"AVAILABILITY")):
    os.makedirs(os.path.join(WORKING_DIR,"AVAILABILITY"))
