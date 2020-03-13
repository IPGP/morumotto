# -*- coding: utf-8 -*-
from datetime import datetime
from django.db import models
from django.utils.timezone import now
from archive.models import Network, Station, DataFile
from plugins.choices import get_plugin_choices
import importlib
import logging

logger = logging.getLogger('Status')

class Component(models.Model):
    COMP_CHOICES =(
    ('Component', 'Display'),
    ('Other', 'Group as Other'),
    ('Disabled', 'Disable'),
    )
    name = models.CharField(max_length=10)
    view_status = models.CharField(
                max_length=50,
                choices=COMP_CHOICES,
                default='Component')

    def __str__(self):
        return self.name


class ChanPath(models.Model):
    archive = models.CharField(max_length=100)

    net = models.CharField(max_length=50)
    sta = models.CharField(max_length=50)
    loc = models.CharField(max_length=10)
    chan = models.CharField(max_length=50)
    chan_path = models.CharField(max_length=100,default=None)

    def save(self, *args, **kwargs):
        self.chan_path = '{0}.{1}.{2}.{3}'.format(self.net, self.sta, self.loc,
                                             self.chan)
        super(ChanPath, self).save(*args, **kwargs)

    def __str__(self):
        return self.chan_path

    class Meta:
        ordering = ('chan_path',)

class CompPath(models.Model):
    archive = models.CharField(max_length=100)

    net = models.CharField(max_length=50)
    sta = models.CharField(max_length=50)
    loc = models.CharField(max_length=10)
    comp = models.CharField(max_length=10)
    comp_path = models.CharField(max_length=50,default=None)

    def save(self, *args, **kwargs):
        self.comp_path = '{0}.{1}.{2}.{3}'.format(self.net, self.sta, self.loc,
                                             self.comp)
        super(CompPath, self).save(*args, **kwargs)

    def __str__(self):
        return self.comp_path

    class Meta:
        ordering = ('comp_path',)

class ArchiveMonitoring(models.Model):
    DATAFORMAT_CHOICES = get_plugin_choices("format")
    METADATAFORMAT_CHOICES = get_plugin_choices("metadata_format")
    STRUCT_CHOICES = get_plugin_choices("structure")

    archive = models.CharField(max_length=100,
                               help_text='Enter the PATH to the archive '
                                         'you want to monitor',
                               unique=True)
    networks = models.ManyToManyField(Network)
    components = models.ManyToManyField(Component)
    stations = models.ManyToManyField(Station)
    start_year = models.IntegerField(
               default=int(datetime.now().year))
    end_year = models.IntegerField(
             default=int(datetime.now().year))


    data_format = models.CharField(
                max_length=50,
                choices=DATAFORMAT_CHOICES,
                default='miniSEED')
    # metadata_format = models.CharField(
    #                 max_length=50,
    #                 choices=METADATAFORMAT_CHOICES,
    #                 default='DatalessSEED')
    struct_type = models.CharField(
                max_length=50,
                choices=STRUCT_CHOICES,
                default='SDS')

    __original_components = None
    __original_stations = None

    def get_data_structure(self):
        # We will instanciate the correct class according to the structure type.
        # See plugins/structure.py
        try:
            module = importlib.import_module("plugins.structure")
            class_ = getattr(module, self.struct_type)
            return class_()
        except:
            logger.error("ERROR: %s has not yet been implemented."
                  " See plugins/structure.py" % struct_type)
            return 1


    def get_data_format(self):
        # We will instanciate the correct class according to the format type.
        # See plugins/format.py
        try:
            module = importlib.import_module("plugins.format")
            class_ = getattr(module, self.data_format)
            return class_()
        except:
            logger.error("ERROR: %s has not yet been implemented."
                  " See plugins/format.py" % data_format)
            return 1

    # def get_metadata_format(self):
    #     # We will instanciate the correct class according to the metadata format
    #     # See plugins/metadata_format.py
    #     try:
    #         module = importlib.import_module("plugins.metadata_format")
    #         class_ = getattr(module, self.metadata_format)
    #         return class_()
    #     except:
    #         logger.error("ERROR: %s has not yet been implemented."
    #               " See plugins/metadata_format.py" % self.metadata_format)
    #         return 1

    def __str__(self):
        return self.archive

    class Meta:
        verbose_name = 'Monitoring setup'
        verbose_name_plural = 'Monitoring setup'


class Stat(models.Model):

    archive_name = models.CharField(max_length=50)
    net = models.CharField(max_length=50)
    sta = models.CharField(max_length=50)
    loc = models.CharField(max_length=10)
    chan = models.CharField(max_length=50)
    comp = models.CharField(max_length=10)

    day = models.DateField('day')
    year = models.CharField(max_length=4)
    starttime = models.DateTimeField('Stream start time')
    endtime = models.DateTimeField('Stream end time')
    modif_time = models.CharField(max_length=50,default=now)

    datafile = models.ForeignKey(DataFile,on_delete=models.CASCADE)
    timestamp = models.IntegerField(default=0)
    ngaps = models.IntegerField(default=0)
    noverlaps = models.IntegerField(default=0)
    gap_span = models.FloatField(default=0)
    overlap_span = models.FloatField(default=0)
    av_new = models.BooleanField(
           default="True",
           verbose_name='Average New')

    def __str__(self):
        return self.datafile.filename

    class Meta:
        verbose_name = 'Statistics'
        verbose_name_plural = 'Statistics'

class AverageStat(models.Model):
    archive_name = models.CharField(max_length=50)
    net = models.CharField(max_length=50)

    a_timestamp = models.IntegerField(default=0)
    a_gap = models.FloatField(default=0)
    a_overlap = models.FloatField(default=0)

    # def get_net(self):
    #     return self.filter(type="3") # ??

    def __str__(self):
        return self.net

    class Meta:
        verbose_name = 'Statistics by Network (average)'
        verbose_name_plural = 'Statistics by Networks (average)'
        ordering = ('net',)


class AverageCompStat(models.Model):
    archive_name = models.CharField(max_length=50)
    net = models.CharField(max_length=50)
    comp = models.CharField(max_length=10)

    a_comp_timestamp = models.IntegerField(default=0)
    a_comp_gap = models.FloatField(default=0)
    a_comp_overlap = models.FloatField(default=0)

    def __str__(self):
        return self.net + self.comp

    class Meta:
        verbose_name = 'Statistics by Component (average)'
        verbose_name_plural = 'Statistics by Components (average)'
        ordering = ('comp',)


class Metrics(models.Model):
    archive_name = models.CharField(max_length=50)

    mean = models.IntegerField(default=0)
    median = models.IntegerField(default=0)
    min = models.IntegerField(default=0)
    max = models.IntegerField(default=0)
    spikes = models.BooleanField(default=False)
    rms = models.IntegerField(default=0)
    data_avalability = models.IntegerField(default=0)
    ngaps = models.IntegerField(default=0)
    noverlaps = models.IntegerField(default=0)

    def __str__(self):
        return self.objects.id


class UpdateStatStatus(models.Model):
    # file_id = models.IntegerField()
    status = models.CharField(max_length=200, default="None")
