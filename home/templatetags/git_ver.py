import os
import subprocess
from django import template

register = template.Library()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

@register.simple_tag
def git_ver():
    '''
    Retrieve and return the latest git commit hash ID and tag as a dict.
    '''

    git_dir = os.path.dirname(BASE_DIR)

    try:
        # Date and hash ID
        head = subprocess.Popen(
            "git -C {dir} log -1 --pretty=format:\"%h on %cd\" --date=short".format(dir=git_dir),
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        version = head.stdout.readline().strip().decode('utf-8')

        # Latest tag
        head = subprocess.Popen(
            "git -C {dir} describe --tags $(git -C {dir} rev-list --tags --max-count=1)".format(dir=git_dir),
            shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        latest_tag = head.stdout.readline().strip().decode('utf-8')

        # git_string = "{v}, {t}".format(v=version, t=latest_tag)
        git_string = "{t}".format(t=latest_tag)
    except:
        git_string = u'unknown'

    return git_string
