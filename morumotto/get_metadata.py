# -*- coding: utf-8 -*-
from .models import LastUpdate
from archive.models import Configuration

logger = logging.getLogger('QC')

last_update = last_update.objects.first()
config = Configuration.objects.first()

if last_update.method == "local_dir":
    dirname = last_update.options
    metadata_from_dir(config, dirname)
elif last_update.method == "web_service":
    client = last_update.options
    metadata_from_webservice(config, client)
elif last_update.method == "svn":
    svn_address, username, password = last_update.options.split(",")
    metadata_from_svn(config, svn_address, username, password)
else:
    logger.error("Metadata automatic update not yet configured, "
                 "please go to /qualitycontrol/update_metadata")
