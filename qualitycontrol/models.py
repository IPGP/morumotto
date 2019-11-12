# -*- coding: utf-8 -*-
from django.db import models
import obspy
import logging
import importlib
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from seismicarchive.models import NSLC
from plugins.choices import get_plugin_choices

LOG_LEVELS = (
    (logging.NOTSET, _('NotSet')),
    (logging.INFO, _('Info')),
    (logging.WARNING, _('Warning')),
    (logging.DEBUG, _('Debug')),
    (logging.ERROR, _('Error')),
    (logging.FATAL, _('Fatal')),
)


class QCConfig(models.Model):
    METADATAFORMAT_CHOICES = get_plugin_choices("metadata_format")
    archive = models.CharField(max_length=200)
    metadata_format = models.CharField(
                    max_length=50,
                    choices=METADATAFORMAT_CHOICES,
                    default='DatalessSEED')

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
    # def save(self, *args, **kwargs):
    #     if QCConfig.objects.exists() and not self.pk:
    #         raise ValidationError('There is can be only one QC instance')
    #     return super(QCConfig, self).save(*args, **kwargs)

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
