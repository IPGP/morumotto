# -*- coding: utf-8 -*-
import os
import importlib
import logging
import tempfile
from datetime import datetime
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from plugins.choices import get_plugin_choices

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKING_DIR =  os.path.join(BASE_DIR, "WORKING_DIR/")
logger = logging.getLogger('Status')

class Network(models.Model):
    name = models.CharField(max_length=10, unique=True)
    def __str__(self):
        return self.name


class Station(models.Model):
    network = models.ForeignKey(Network,on_delete=models.CASCADE)
    name = models.CharField(max_length=10)
    multiplexing = models.BooleanField(default="False",
                                       verbose_name="Multiplexed Channels")

    def __str__(self):
        name_to_display = "[%s] %s" %(self.network.name, self.name)
        return name_to_display

    class Meta:
        ordering = ('network','name',)


class Location(models.Model):
    name = models.CharField(max_length=10, unique=True)
    def __str__(self):
        return self.name


class Channel(models.Model):
    name = models.CharField(max_length=10, unique=True)
    def __str__(self):
        return self.name


class NSLC(models.Model):
    net = models.ForeignKey(Network,on_delete=models.CASCADE,
                            verbose_name="network")
    sta = models.ForeignKey(Station,on_delete=models.CASCADE,
                            verbose_name="station")
    loc = models.ForeignKey(Location,on_delete=models.CASCADE,
                            verbose_name="location")
    chan = models.ForeignKey(Channel,on_delete=models.CASCADE,
                            verbose_name="channel")
    code = models.CharField(max_length=50,default=None)

    def save(self, *args, **kwargs):
        self.code = '{0}.{1}.{2}.{3}'.format(self.net.name, self.sta.name,
                                             self.loc, self.chan)
        super(NSLC, self).save(*args, **kwargs)

    def __str__(self):
        return self.code

    class Meta:
        ordering = ('net','sta','chan')
        verbose_name = 'N.S.L.C.'
        verbose_name_plural = 'N.S.L.C'

class PluginField(models.Field):
    def __init__(self, type, *args, **kwargs):
        self.max_length = max_length
        super().__init__(*args, **kwargs)

    def db_type(self, connection):
        return 'char(%s)' % self.max_length


class Source(models.Model):
    SOURCE_LOG_CHOICES =(
        (1, '1 : Error'),
        (2, '2 : Warning'),
        (3, '3 : Debug'),
    )
    SOURCE_CHOICES = get_plugin_choices("source")
    name = models.CharField(
         max_length=50,
         help_text='Please avoid spaces (they will automaticaly '
                   'be replaced with underscores)')
    priority = models.PositiveIntegerField(
             default=1,
             help_text='1 is the highest priority',
             validators=[MinValueValidator(1)],
             )
    log_level = models.IntegerField(
              choices=SOURCE_LOG_CHOICES,
              default=3)
    type = models.CharField(
         max_length=50,
         choices=SOURCE_CHOICES,
         verbose_name="Plugin",
         )
    parameters = models.CharField(max_length=50,blank=True)
    limit_rate = models.IntegerField(
               default=0,
               verbose_name="Downloading limit rate",
               help_text='Limit for downloading rate, '
                         'in Kb/s. 0 is for unlimited')

    is_online = models.BooleanField(default=True)
    availability = models.BooleanField(
                 default=True,
                 help_text='If False (unselected), '
                           'the software will assume that data is '
                           'always available for all time')
    nslc = models.ManyToManyField(NSLC,verbose_name='N.S.L.C',
                                  help_text=('Select all NSLC that this source'
                                             ' will query, unselected will be'
                                             ' ignored.')
                                 )

    def __str__(self):
        return self.name

    def get_plugin(self):
        # We will instanciate the correct class according to the source type.
        # See plugins/source.py
        try:
            module = importlib.import_module("plugins.source")
            class_ = getattr(module, self.type)
            return class_()
        except:
            logger.error("ERROR: %s has not yet been correctly implemented."
                  " See plugins/source.py" % self.type)
            return 1

    # def get_parameters_template(self):
    #     # Returns template for parameters.
    #     # See plugins/source.py
    #     try:
    #         module = importlib.import_module("plugins.source")
    #         class_ = getattr(module, self.type)
    #         return class_().template
    #     except:
    #         logger.error("ERROR: %s has not yet been correctly implemented."
    #               " See plugins/source.py" % self.type)
    #         return 1

    def save(self, *args, **kwargs):
        self.name = self.name.replace(" ", "_")
        super(Source, self).save(*args, **kwargs)

    class Meta:
        ordering = ('priority',)


class Configuration(models.Model):
    FREQ_CHOICES =(
        ('hourly', 'Hours'),
        ('daily', 'Days'),
    )
    LIFESPAN_CHOICES = (
        ('n', 'Number of retry'),
        ('p', 'Period (in hours)'),
    )
    BLOCKSIZE_CHOICES = (
        (512,512),
        (4096,4096),
    )

    COMPRESS_CHOICES =(
        ('STEIM1', 'STEIM1'),
        ('STEIM2', 'STEIM2'),
        ('INT_16', 'INT_16'),
        ('INT_32','INT_32'),
        ('INT_24','INT_24'),
		('IEEE_FP_SP', 'IEEE_FP_SP'),
        ('IEEE_FP_DP','IEEE_FP_DP'),
    )

    QC_CHOICES =(
        ('D', 'D (indeterminate)'),
        ('R', 'R (raw waveform)'),
        ('Q', 'Q (quality controlled data)'),
        ('M', 'M (data center modified)'),
    )

    DATAFORMAT_CHOICES = get_plugin_choices("format")
    # METADATAFORMAT_CHOICES = get_plugin_choices("metadata_format")
    STRUCT_CHOICES = get_plugin_choices("structure")

    config_name = models.CharField(
                max_length=50,
                default="SIQACO_CONFIG")
    archive = models.CharField(
            max_length=50,
            help_text='Absolute path to your final archive',
            default=os.path.join(BASE_DIR,"final_archive"))

    networks = models.ManyToManyField(Network)
    stations = models.ManyToManyField(Station)
    nslc = models.ManyToManyField(NSLC,verbose_name='N.S.L.C')
    sources = models.ManyToManyField(Source, blank=True)
    data_format = models.CharField(
                max_length=50,
                choices=DATAFORMAT_CHOICES,
                default='SEED')
    # metadata_format = models.CharField(
    #                 max_length=50,
    #                 choices=METADATAFORMAT_CHOICES,
    #                 default='DatalessSEED')
    struct_type = models.CharField(
                max_length=50,
                choices=STRUCT_CHOICES,
                default='SDS',
                verbose_name='Structure type')
    blocksize = models.PositiveSmallIntegerField(
              choices=BLOCKSIZE_CHOICES,
              default=4096,
              verbose_name='Blocksize, in bytes')
    compression_format = models.CharField(
                       max_length=50,
                       choices=COMPRESS_CHOICES,
                       default='STEIM2')
    quality_label = models.CharField(
                  max_length=5,
                  choices=QC_CHOICES,
                  default='M')
    request_lifespan_type = models.CharField(
                          max_length=50,
                          choices=LIFESPAN_CHOICES,
                          default='n')
    request_lifespan = models.PositiveSmallIntegerField(
                     default=5,
                     validators=[MinValueValidator(1)],
                     help_text='Either a number of retry OR '
                               'a lifespan in hours '
                               '(depending on the previous field)')
    n_request = models.PositiveSmallIntegerField(
              default=10,
              validators=[MinValueValidator(1), MaxValueValidator(100)],
              help_text='Number of request parallel threads')
    max_gaps_by_analysis = models.PositiveSmallIntegerField(
                         default=10,
                         validators=[MinValueValidator(1)],
                         help_text='Over this threshold, the analysis '
                                   'will merge gaps together')
    initialisation = models.BooleanField(
                   default=True,
                   help_text='Check if you want to initialise '
                             'the software again (not recommanded)')
    debug_mode = models.BooleanField(
               default=True,
               help_text='Check if you want to keep all data downloaded '
                         'for patching')
    crontab_status = models.BooleanField(
                   default=False,
                   help_text='True if a crontab is running, else False')
    granularity_type = models.CharField(
                     max_length=6,
                     choices=FREQ_CHOICES,
                     default='hourly')
    f_analysis = models.PositiveSmallIntegerField(
               default=1,
               validators=[MinValueValidator(1)],
               help_text='Either in hours or days '
                         '(depending on granularity)',
               verbose_name='Frequency for new analysis')
    w_analysis = models.PositiveSmallIntegerField(
               default=2,
               validators=[MinValueValidator(1)],
               help_text='Either in '
                         'hours or days (depending on granularity)',
               verbose_name='Length of the analysis window')
    l_analysis = models.PositiveSmallIntegerField(
               default=1,
               help_text='The analysis will end at NOW-LATENCY, e.g. if now is '
                         '12:00 and latency is 2 hours, the analysis will end '
                         'at 10:00 today). '
                         'Can be either in hours or days (depending on '
                         'granularity)',
               verbose_name='Latency of analysis')

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

    # def save(self, *args, **kwargs):
    #     if Configuration.objects.exists() and not self.pk:
    #         raise ValidationError('There is can be only one Configuration instance')
    #     return super(Configuration, self).save(*args, **kwargs)

    def __str__(self):
        return self.config_name

    class Meta:
        ordering = ('config_name',)


class DataFile(models.Model):
    # archive = models.CharField(max_length=200, default="/home/geber/SiQaCo/siqaco_project/final_archive")
    key = models.CharField(max_length=200)
    filename = models.CharField(max_length=200)
    modif_time = models.FloatField(max_length=200,default=None)
    stream_starttime = models.DateTimeField('data_starttime',default=now)
    stream_endtime = models.DateTimeField('data_endtime',default=now)

    def __str__(self):
        return self.filename


class Overlap(models.Model):
    starttime = models.DateTimeField('starttime')
    endtime = models.DateTimeField('endtime')
    leapsecond = models.BooleanField(default=False)
    archive = models.CharField(max_length=200)
    nslc = models.ForeignKey(NSLC,verbose_name='N.S.L.C',
                             on_delete=models.CASCADE)

    def __str__(self):
        return self.pk.__str__()


class Gap(models.Model):
    starttime = models.DateTimeField()
    endtime = models.DateTimeField()
    archive = models.CharField(max_length=200)
    nslc = models.ForeignKey(NSLC,on_delete=models.CASCADE,
                             verbose_name='N.S.L.C')
    status = models.CharField(max_length=200, default="new")
    files = models.ManyToManyField(DataFile,
                                   verbose_name='File(s) concerned',
                                   blank=True)

    class Meta:
        ordering = ("endtime",)
        get_latest_by = "endtime"

    def __str__(self):
        return self.pk.__str__()

class GapList(models.Model):
    # That one is just to create new requests
    starttime = models.DateTimeField()
    endtime = models.DateTimeField()
    nslc_list = models.ManyToManyField(NSLC, verbose_name='N.S.L.C')

    def __str__(self):
        return self.pk.__str__()



class SourceAvailability(models.Model):
    source = models.ForeignKey(
           Source,
           on_delete=models.CASCADE,
           default=None)
    nslc = models.ForeignKey(
         NSLC, on_delete=models.CASCADE,
         default=None,
         verbose_name='N.S.L.C')
    starttime = models.DateTimeField('starttime')
    endtime = models.DateTimeField('endtime')

    class Meta:
        get_latest_by = "endtime"

    def __str__(self):
        return self.source.name

    class Meta:
        verbose_name = 'Source availability'
        verbose_name_plural = 'Source availabilities'

class SourceAvailabilityStat(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE,default=None)
    nslc = models.ForeignKey(NSLC,verbose_name='N.S.L.C',
                             on_delete=models.CASCADE)
    day = models.DateField('Day', default=now)
    data_avail = models.IntegerField(default=0)

    def __str__(self):
        return self.source.name


class SourceOnlineStat(models.Model):
    source = models.ForeignKey(Source,on_delete=models.CASCADE)
    day = models.DateField('Day', default=now)
    daily_failure = models.IntegerField(default=0)

    def __str__(self):
        return self.source.name


class AppLogs(models.Model):
    # AppLogs objects contain errors and warnings
    # generated during system operations
    warning = models.CharField(max_length=200)
    error = models.CharField(max_length=200)
    date = models.DateTimeField('log date')

    def __str__(self):
        return self.date


# --------------------- Request related classes --------------------------------
class Postfile(models.Model):
    source = models.ForeignKey(Source,on_delete=models.CASCADE,default=None)
    filename = models.CharField(max_length=200, default=None)

    # def delete(self, *args, **kwargs):
    #     # When postfile has been processed, we remove it
    #     try:
    #         os.remove(self.filename)
    #     except Exception as e:
    #         print("can't remove postfile %s" %self.filename)
    #         raise e
    #     super(Postfile, self).delete(*args, **kwargs)

    def __str__(self):
        return self.filename


class Request(models.Model):
    # network = models.ForeignKey(Network,on_delete=models.CASCADE)
    # station = models.ForeignKey(Station,on_delete=models.CASCADE)
    gap = models.ForeignKey(Gap,on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    starttime = models.DateTimeField('Gap start time')
    endtime = models.DateTimeField('Gap end time')
    workspace = models.CharField(max_length=50)
    postfile = models.ManyToManyField(Postfile)
    timeout = models.IntegerField(default=0)

    tempdir = models.CharField(max_length=250,default=None,null=True)

    # # Create a tempfile in which the request will handle temporary data
    # def save(self, *args, **kwargs):
    #     if self.tempdir == None:
    #         self.tempdir = tempfile.mkdtemp(
    #                      dir=os.path.join(WORKING_DIR,"PATCH/"),
    #                      prefix="%s_" %self.id)
    #     print("self.tempdir on save", self.tempdir)
    #     super(Request, self).save(*args, **kwargs)

    def __str__(self):
        return self.status


class RequestStack(models.Model):
    pass


class RequestHistory(models.Model):
    # keeps history of archived requests
    exec_date = models.DateTimeField('log date')
    # status = models.CharField(max_length=200)
    n_retry = models.IntegerField(default=0)


class SystemAvailability(models.Model):
    cpu_max_load = models.IntegerField(default=100)
    bandwidth_max = models.IntegerField(default=10)

    def __str__(self):
        return self.objects.id
