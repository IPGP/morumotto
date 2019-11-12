# -*- coding: utf-8 -*-
from home.forms import LoginForm

def my_login_form(request):
    return {
        'login_form': LoginForm(),
    }
