# -*- coding: utf-8 -*-
import os
import re
import obspy
import logging
import importlib
from fnmatch import fnmatch
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from archive.models import NSLC
from plugins.choices import get_plugin_choices

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN =  os.path.join(BASE_DIR, "bin")
VALIDATOR_LINK = os.path.join(BASE_DIR, "bin","stationxml-validator.jar")

LOG_LEVELS = (
    (logging.NOTSET, _('NotSet')),
    (logging.INFO, _('Info')),
    (logging.WARNING, _('Warning')),
    (logging.DEBUG, _('Debug')),
    (logging.ERROR, _('Error')),
    (logging.FATAL, _('Fatal')),
)


def get_validator_choices():
    VALIDATOR_CHOICES = ()
    validator_list = [f for f in os.listdir(BIN) if
                      ( os.path.isfile(os.path.join(BIN, f))
                      and not os.path.islink(os.path.join(BIN, f))
                      and fnmatch(f, '*.jar') ) ]
    for validator in validator_list:
        ver = '.'.join(re.findall(r"[\d']+", validator))
        VALIDATOR_CHOICES += ((validator,ver),)

    return VALIDATOR_CHOICES


class QCConfig(models.Model):
    METADATAFORMAT_CHOICES = get_plugin_choices("metadata_format")
    archive = models.CharField(max_length=200)
    metadata_format = models.CharField(
                    max_length=50,
                    choices=METADATAFORMAT_CHOICES,
                    default='stationXML')
    metadata_validator = models.CharField(
                       max_length=50,
                       choices=get_validator_choices(),
                       default='1.5.9.5',
                       verbose_name="Metadata Validator Version",)

    def get_metadata_format(self):
        # We will instanciate the correct class according to the metadata format
        # See plugins/metadata_format.py
        try:
            module = importlib.import_module("plugins.metadata_format")
            class_ = getattr(module, self.metadata_format)
            return class_()
        except:
            logger.error("ERROR: %s has not yet been implemented."
                  " See plugins/metadata_format.py" % self.metadata_format)
            return 1
    #
    def save(self, *args, **kwargs):
        print("valid:",self.metadata_validator )
        validator_file = os.path.join(BASE_DIR, "bin",self.metadata_validator)
        if os.path.exists(VALIDATOR_LINK):
            os.remove(VALIDATOR_LINK)
        os.symlink(validator_file, VALIDATOR_LINK)
        return super(QCConfig, self).save(*args, **kwargs)

    def __str__(self):
        return self.archive

    class Meta:
        verbose_name_plural = verbose_name = 'Quality Control Configuration'


class Message(models.Model):
    TYPE_CHOICES = (
        (('info'), ('Info')),
        (('warning'), ('Warning')),
        (('debug'), ('Debug')),
        (('error'), ('Error')),
    )

    msg = models.CharField(max_length=200)
    type = models.CharField(max_length=25,
                            choices=TYPE_CHOICES,
                            default="info")
    def __str__(self):
        return self.msg


class Metadata(models.Model):

    nslc = models.ForeignKey(NSLC, on_delete=models.CASCADE,
                             verbose_name="N.S.L.C.")
    file = models.CharField(max_length=200)
    lon = models.FloatField(validators=[MinValueValidator(-180.0),
                                        MaxValueValidator(180.0)],
                            help_text="Must be a decimal value")
    lat = models.FloatField(validators=[MinValueValidator(0.0),
                                        MaxValueValidator(90.0)],
                            help_text="Must be a decimal value")
    messages = models.ManyToManyField(Message)


    def __str__(self):
        return self.nslc.code

    class Meta:
        ordering = ('nslc',)
        verbose_name_plural = verbose_name = 'Metadata'


class LastUpdate(models.Model):
    UPDATE_CHOICES=(
        ("local_dir", 'Select local dir/'),
        ("web_service", 'Use a webservice'),
        ("svn", 'Use SVN'),
    )
    time = models.DateTimeField(default=now)
    update_method = models.CharField(max_length=25,
                                     choices=UPDATE_CHOICES,
                                     default="local_dir")
    options = models.CharField(max_length=200,default="")
    class Meta:
         verbose_name = "Last Update of Metadata"
         verbose_name_plural = "Last Update of Metadata"

    def __str__(self):
        return "Last Update on %s with data from %s" %(self.time,
                                                       self.update_method)
