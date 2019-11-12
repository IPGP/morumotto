# -*- coding: utf-8 -*-
from django import forms
from django.contrib import admin
from .models import Stat, Component, AverageStat, AverageCompStat, \
    ChanPath, CompPath, ArchiveMonitoring
from django.core.exceptions import ValidationError
from . import update_monitoring


class ArchiveMonitoringForm(forms.ModelForm):
    class Meta:
        model = ArchiveMonitoring
        fields = "__all__"

    def clean(self):
        archive = self.cleaned_data.get('archive')
        networks = self.cleaned_data.get('networks')
        stations = self.cleaned_data.get('stations')
        components = self.cleaned_data.get('components')
        start_year = self.cleaned_data.get("start_year")
        end_year = self.cleaned_data.get("end_year")

        net_list = [net.name for net in networks]
        error_sta_list = []
        for sta in stations:
            if sta.network.name not in net_list:
                error_sta_list.append(sta.name)
        if error_sta_list != []:
            raise ValidationError({'stations':'Station(s) %s not in '
                                              'Network(s) %s'
                                               % (error_sta_list,
                                                  net_list)})

        if start_year > end_year :
            raise ValidationError({'end_year':"End year must be later or "
                                              "equal to start year"})

        update_monitoring.update_average_stats(networks,stations,components,
                                               archive, start_year, end_year)
        return self.cleaned_data

class ArchiveMonitoringAdmin(admin.ModelAdmin):
    form = ArchiveMonitoringForm
    list_display = ('archive', 'start_year', 'end_year')
    filter_horizontal = ('networks','components','stations',)


class StatAdmin(admin.ModelAdmin):
    list_display = ('datafile', 'archive_name', 'net', 'sta', 'loc', 'chan', 'day')
    list_filter = ('archive_name','net','chan', 'day')
    exclude = ('av_new',)
    search_fields = ['datafile__filename']

class ComponentAdmin(admin.ModelAdmin):
    list_display = ('name', 'view_status')
    list_filter = ('view_status',)

class AverageStatAdmin(admin.ModelAdmin):
    list_display = ('net','archive_name')
    list_filter = ('archive_name','net')

class AverageCompStatAdmin(admin.ModelAdmin):
    list_display = ('net', 'comp','archive_name')
    list_filter = ('archive_name','net','comp')

class CompPathAdmin(admin.ModelAdmin):
    list_display = ('comp_path', 'net', 'sta','loc','comp','archive')
    list_filter = ('archive', 'net', 'sta','loc','comp')


class ChanPathAdmin(admin.ModelAdmin):
    list_display = ('chan_path', 'net', 'sta','loc','chan','archive')
    list_filter = ('archive', 'net', 'sta','loc','chan')


# admin.site.site_url = "/monitoring"
admin.site.register(ArchiveMonitoring,ArchiveMonitoringAdmin)
admin.site.register(Stat,StatAdmin)
admin.site.register(Component,ComponentAdmin)
admin.site.register(AverageStat,AverageStatAdmin)
admin.site.register(AverageCompStat,AverageCompStatAdmin)
admin.site.register(ChanPath,ChanPathAdmin)
admin.site.register(CompPath,CompPathAdmin)
