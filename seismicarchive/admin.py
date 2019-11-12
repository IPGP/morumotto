# -*- coding: utf-8 -*-
from os import remove
from django import forms
from django.contrib import admin
from django.utils.html import format_html
from .models import Configuration, NSLC, Network, Station, Location, Channel, \
    DataFile, Gap, Source, Request, Postfile, SourceAvailability, \
    SourceOnlineStat, SourceAvailabilityStat, GapList
# from django.core.exceptions import ValidationError
from siqaco import cronjobs
from plugins.choices import get_sources_templates

# Register your models here.

# ovs_admin : doit pouvoir effectuer la configuration du logiciel.
# to change password : manage.py changepassword <user_name>
# ovs_obs : utilisateur avec des droits limités


def has_changed(instance, field):
    if not instance.pk:
        return False
    old_value = instance.__class__._default_manager.filter(pk=instance.pk).values(field).get()[field]
    return not getattr(instance, field) == old_value


class ConfigForm(forms.ModelForm):
    class Meta:
        model = Configuration
        # exclude = ('nslc',)
        fields = "__all__"



    def clean(self):
        if (self.cleaned_data.get('networks') and
            self.cleaned_data.get('stations')):
            net_list = [net.name for net in self.cleaned_data.get('networks')]
            stations = self.cleaned_data.get('stations')
            error_sta_list = []
            for sta in stations:
                if sta.network.name not in net_list:
                    error_sta_list.append(sta.name)

            if error_sta_list != []:
                raise forms.ValidationError({'stations':'Station(s) %s not in '
                                                  'Network(s) %s'
                                                   % (error_sta_list,
                                                      net_list)})

        f_analysis = self.cleaned_data.get("f_analysis")
        l_analysis = self.cleaned_data.get("l_analysis")
        w_analysis = self.cleaned_data.get("w_analysis")
        if w_analysis < f_analysis :
            raise forms.ValidationError({'f_analysis': ['Frequency of analysis '
                                                'must be <= to '
                                                'the analysis Window'],
                                   'w_analysis':['Analysis window must be >= '
                                                'to the frequency of analysis'],
                                  })
        if Configuration.objects.exists() and not self.instance.pk:
            raise forms.ValidationError('There can be only 1 Configuration')
        return self.cleaned_data


class ConfigurationAdmin(admin.ModelAdmin):
    form = ConfigForm
    readonly_fields = ['nslc']
    exclude = ('crontab_status',)
    filter_horizontal = ('nslc','networks','stations','sources',)
    fieldsets = (
        ('Setup', {
           'fields': ['config_name', 'initialisation', 'debug_mode']
        }),
        ('Output options', {
           'fields': ['archive', 'data_format',
                      'struct_type',
                       'blocksize', 'compression_format',
                       'quality_label'],
        }),
        ('Update setting', {
            'fields': ['networks', 'stations', 'sources',
                       'request_lifespan_type',
                       'request_lifespan', 'n_request',
                       'max_gaps_by_analysis',],
        }),
        ('Window of analysis', {
            'fields': ['granularity_type',
                       'f_analysis','w_analysis','l_analysis'],
        }),
        ('Info', {
            'fields': ['nslc',],
        }),
    )


    def save_related(self, request, form, formsets, change):
        super(ConfigurationAdmin, self).save_related(request, form, formsets, change)
        config = form.instance
        networks = config.networks.all()
        stations = config.stations.all()
        nslc_list = []
        for net in networks:
            for sta in stations.filter(network__name=net.name):
                for nslc in NSLC.objects.filter(net__name=net.name, sta__name=sta.name):
                    nslc_list.append(nslc)
                    if not config.nslc.filter(pk=nslc.pk).exists():
                        config.nslc.add(nslc)
        for nslc in config.nslc.all():
            if nslc not in nslc_list:
                config.nslc.remove(nslc)

    def save_model(self, request, obj, form, change):
        if (has_changed(obj,"f_analysis") or
            has_changed(obj,"w_analysis") or
            has_changed(obj,"l_analysis")):
            cronjobs.change_crontab(obj)
        super().save_model(request, obj, form, change)



class NSLCAdmin(admin.ModelAdmin):
    list_display = ('code', 'net', 'sta', 'loc', 'chan','is_mux')
    list_filter = ("net", "loc", "chan", "sta")
    search_fields = ['code']
    def is_mux(self, obj):
        return obj.sta.multiplexing
    is_mux.boolean = True
    is_mux.short_description = "Multiplexed Channels"


class GapAdmin(admin.ModelAdmin):
    list_display = ('pk', 'get_code',
                    'starttime_microseconds',
                    'endtime_microseconds',
                    'status')
    list_filter = ("nslc__net","nslc__loc","nslc__chan","nslc__sta",)
    search_fields = ["nslc__code","pk"]
    # The following lines are useful to display a related ForeignKey
    # In our case it's the nslc_code
    def get_code(self, obj):
        return obj.nslc.code
    get_code.short_description = 'NSLC'
    get_code.admin_order_field = 'nslc__code'
    # Following method reduces the time to display the page
    def starttime_microseconds(self, obj):
        return obj.starttime.strftime("%Y %m %d %H:%M:%S,%f")
    starttime_microseconds.admin_order_field = 'timefield'
    starttime_microseconds.short_description = 'Precise Starttime'

    def endtime_microseconds(self, obj):
        return obj.endtime.strftime("%Y %m %d %H:%M:%S,%f")
    endtime_microseconds.admin_order_field = 'timefield'
    endtime_microseconds.short_description = 'Precise Endtime'
    def get_queryset(self, request):
        return super(GapAdmin,self).get_queryset(request).select_related('nslc')


class SourceForm(forms.ModelForm):
    class Media:
        js = ('home/js/admin_source.js',)
    class Meta:
        model = Source
        fields = "__all__"
        widgets = {
            'parameters': forms.TextInput(attrs={'placeholder':'(See examples below)'}),
        }

    def __init__(self, *args, **kwargs):
        super(SourceForm, self).__init__(*args, **kwargs)
        help_text = ""
        for t,p in get_sources_templates().items():
            help_text += "Type: %s, parameters: %s <br>" %(t,p)
        self.fields['parameters'].help_text = help_text


    # We're going to check if the stations in NSLC don't have another source
    # with the same priority
    def clean(self):
        nslcs = self.cleaned_data.get('nslc')
        if nslcs:
            priority = self.cleaned_data.get('priority')
            id = self.instance.pk
            for nslc in nslcs:
                already_in = Source.objects.filter(
                           priority=priority, nslc=nslc).exclude(id=id)
                if already_in:
                    raise forms.ValidationError({'nslc':'%s already uses %s'
                                                  ' with priority %s'
                                                  % (nslc,
                                                     already_in.first().name,
                                                     priority)})
            return self.cleaned_data



class SourceAdmin(admin.ModelAdmin):
    form = SourceForm
    save_as = True
    exclude = ('is_online',)
    list_display = ('name', 'type','priority', 'parameters', 'limit_rate','id')
    filter_horizontal = ('nslc',)
    search_fields = ["name"]


class SourceAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('source', 'nslc', 'starttime', 'endtime')
    list_filter = ("source",  "nslc__net","nslc__loc","nslc__chan","nslc__sta",)
    search_fields = ["nslc__code",]


class SourceOnlineStatAdmin(admin.ModelAdmin):
    list_display = ('source', 'day', 'daily_failure', 'pk')
    list_filter = ("source", "day")


class SourceAvailabilityStatAdmin(admin.ModelAdmin):
    list_display = ('source', 'nslc', 'day', 'data_avail', 'pk')
    list_filter = ("source", "nslc__net","nslc__loc","nslc__chan","nslc__sta",)


def put_on_hold(modeladmin, request, queryset):
    queryset.update(status="on_hold")
put_on_hold.short_description = "Put selected requests to 'on_hold'"


def cancel_request(modeladmin, request, queryset):
    queryset.update(status="cancelled")
cancel_request.short_description = "Cancel selected requests (not deleting it)"


class RequestAdmin(admin.ModelAdmin):
    list_display = ('pk', 'get_code', 'get_gap', 'starttime', 'endtime', 'workspace','status','is_mux')
    actions = [put_on_hold, cancel_request]
    readonly_fields = ['is_mux']
    def get_code(self, obj):
        if obj.gap.nslc.sta.multiplexing:
            list = [ o.code for o in
                     NSLC.objects.filter(net=obj.gap.nslc.net,
                                         sta=obj.gap.nslc.sta) ]
        else:
            list = [obj.gap.nslc.code]
        return list
    get_code.short_description = 'NSLC'
    get_code.admin_order_field = 'gap__nslc__code'

    def is_mux(self,obj):
        return obj.gap.nslc.sta.multiplexing
    is_mux.short_description = 'Multiplexed Channels'
    is_mux.admin_order_field = 'gap'
    is_mux.boolean = True

    def get_gap(self,obj):
        return obj.gap.pk
    get_gap.short_description = 'Gap'
    get_gap.admin_order_field = 'gap'
    def get_queryset(self, request):
        return super(RequestAdmin,self).get_queryset(request).select_related('gap')


def make_mux(modeladmin, request,queryset):
    queryset.update(multiplexing=True)
make_mux.short_description = "Mark station(s) as multiplexed"

def make_demux(modeladmin, request,queryset):
    queryset.update(multiplexing=False)
make_demux.short_description = "Mark station(s) as demultiplexed"




class StationAdmin( admin.ModelAdmin):
    list_display = ('name', 'related_net', 'multiplexing')
    list_filter = ("network__name",)
    search_fields = ["nslc__code"]
    actions = [make_mux, make_demux]
    def related_net(self, obj):
        return obj.network.name
    related_net.short_description = 'Related Network'
    related_net.admin_order_field = 'network__name'

#
# def remove_file(modeladmin, request, queryset):
#     for obj in queryset:
#         try:
#             print("obj.filename", obj.filename)
#             remove(obj.filename)
#         except:
#             print("can't remove datafile %s" %obj.filename)
#         # Gap.objects.filter(files__in=obj).delete()
#         queryset.delete()
#
# remove_file.short_description = ("Delete selected data files and remove "
#                                  "physical file")

class DataFileAdmin(admin.ModelAdmin):
    list_display = ('pk', 'key', 'filename', 'modif_time')
    search_fields = ["filename", 'key']
    # actions = [remove_file]


class PostfileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'source')
    list_filter = ("source",)
    search_fields = ['filename']

# The two following classes, GapInLine and GapListAdmin provide an interface
# for the user to be able to see gaps and overlaps
# class GapInLine(admin.TabularInline):
#     model = GapList.gap.through
    # fields = ['show_starttime','show_endtime','show_status',]
    # readonly_fields = ['show_starttime','show_endtime','show_status',]
    # def show_status(self, instance):
    #     return instance.gap.status
    # def show_starttime(self, instance):
    #     return instance.gap.starttime
    # def show_endtime(self, instance):
    #     return instance.gap.endtime
    # show_status.short_description = 'Status'
    # show_starttime.short_description = 'Start'
    # show_endtime.short_description = 'End'

#
# class GapListAdmin(admin.ModelAdmin):
#     list_display = ('id', 'network', 'station', 'location', 'channel')
#     # inlines = [
#     #     GapInLine,
#     # ]
#
#
#
# class OverlapAdmin(admin.ModelAdmin):
#     list_display = ('id', 'starttime', 'endtime')



admin.site.register(Configuration,ConfigurationAdmin)
admin.site.register(NSLC,NSLCAdmin)
admin.site.register(Network)
admin.site.register(Station, StationAdmin)
admin.site.register(Location)
admin.site.register(Channel)
admin.site.register(DataFile,DataFileAdmin)
admin.site.register(Gap,GapAdmin)
admin.site.register(GapList)
# admin.site.register(Stat,StatAdmin)
admin.site.register(Source, SourceAdmin)
admin.site.register(Request,RequestAdmin)
admin.site.register(Postfile,PostfileAdmin)
admin.site.register(SourceAvailability,SourceAvailabilityAdmin)
admin.site.register(SourceOnlineStat,SourceOnlineStatAdmin)
admin.site.register(SourceAvailabilityStat,SourceAvailabilityStatAdmin)
