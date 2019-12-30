# -*- coding: utf-8 -*-
import datetime
from django import forms
from django.db import models
from django.forms import modelformset_factory, formset_factory, BaseModelFormSet
from form_utils.forms import BetterForm, BetterModelForm
from archive.models import Configuration, Network, Request, Gap, Source
from monitoring.models import ArchiveMonitoring
from qualitycontrol.models import QCConfig


class ConfigurationForm(BetterModelForm):

    class Meta:
        model = Configuration
        fields = "__all__"
        exclude = ('networks', 'stations','nslc','name',
                   'initialisation', 'crontab_status','source')
        widgets = {
            'archive': forms.TextInput(attrs={'class':'input-control'}),
            'f_analysis': forms.NumberInput(attrs={'onchange':'update_value()'}),
            'w_analysis': forms.NumberInput(attrs={'onchange':'update_value()'}),
            'l_analysis': forms.NumberInput(attrs={'onchange':'update_value()'}),
            'granularity_type': forms.Select(attrs={'onchange':'update_value()'}),
            }
        fieldsets = (
            ('Final Archive options', {
               'fields': ['archive', 'data_format',
                          'metadata_format', 'struct_type',
                           'blocksize', 'compression_format',
                           'quality_label'],
            }),
            ('Update settings (*)', {
                'fields': ['request_lifespan_type',
                           'request_lifespan', 'n_request',
                           'max_gaps_by_analysis','sources',],
            }),
            ('Window of analysis', {
                'fields': ['granularity_type',
                           'f_analysis','w_analysis','l_analysis','crontime'],
            }),

        )
    def __init__(self, *args, **kwargs):
        # This is to have a popover help for each fields
        super(ConfigurationForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            if help_text != '':
                self.fields[field].widget.attrs.update({'class':'has-popover',
                                                        'title':help_text,
                                                        'data-placement':'right',
                                                        'data-container':'body'})
        self.fields['archive'].widget.attrs.update({'class' : 'archive-path'})

    def clean(self):
        cleaned_data = super(ConfigurationForm, self).clean()
        f_analysis = cleaned_data.get("f_analysis")
        l_analysis = cleaned_data.get("l_analysis")
        w_analysis = cleaned_data.get("w_analysis")
        if w_analysis <= f_analysis :
            msg=('Wrong parameters : Frequency to new analysis must be '
                'smaller than the analysis Window')
            self.add_error("f_analysis", msg)


class SourceForm(forms.ModelForm):
    class Meta:
        model = Source
        fields = "__all__"
        exclude=('is_online',)
        widgets = {
            # 'parameters': forms.TextInput(attrs={'placeholder': '(See plugins)'}),
            'type': forms.Select(attrs={'onchange': 'get_template()'}),
            'parameters': forms.TextInput(attrs={'size': 30,}),
            }

    def __init__(self, *args, **kwargs):
        # This is to have a popover help for each fields
        super(SourceForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            if help_text != '':
                self.fields[field].widget.attrs.update({'class':'has-popover',
                                                        'title':help_text,
                                                        'data-placement':'right',
                                                        'data-container':'body'})


class NetworkFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        super(NetworkFormSet, self).__init__(*args, **kwargs)
        for form in self.forms:
            form.empty_permitted = False


NetworkModelFormset = modelformset_factory(
    Network,
    fields=('name', ),
    extra=1,
    labels = {
            "name": "Network",
        },
    widgets={'name': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter network code here'
        })
    }
)


class WebServiceForm(forms.Form):
    CLIENT_CHOICES = (("IRIS","IRIS"),)
    networks = forms.CharField(
             label='Networks',
             help_text= ('To enter multiple networks, separate them with a coma'
                         '\nExample : GL, PF, MQ'),
             widget=forms.TextInput(attrs={'placeholder':
                                           'Enter network(s) name',}),
             )
    from obspy.clients.fdsn.header import URL_MAPPINGS
    for key in sorted(URL_MAPPINGS.keys()):
        if key != "IRIS":
            CLIENT_CHOICES += ((key,key),)
    name = forms.CharField(
            label='Client',
            initial="IRIS",
            help_text= ('See "FDSN web service client for ObsPy"'),
            widget=forms.Select(choices=CLIENT_CHOICES),
            # help_text="It will get all Stations, Locations and Channels "
            # "available for the network(s) that you have previously
            # defined in the admin page",
        )
    custom_url = forms.CharField(
               label='Custom URL',
               initial="",
               required=False,
               help_text= ('Use a custom url, e.g. "service.iris.edu"'),
               widget=forms.TextInput(attrs={'placeholder':
                                             'Leave empty to use "Client"',}),
               )

    def __init__(self, *args, **kwargs):
        # This is to have a popover help for each fields
        super(WebServiceForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            if help_text != '':
                self.fields[field].widget.attrs.update({'class':'has-popover',
                                                        'title':help_text,
                                                        'data-placement':'right',
                                                        'data-container':'body'})

class FileForm(forms.Form):
    filename = forms.FileField()


class StationXMLForm(forms.Form):
    stationxmlfile = forms.FileField()
    def __init__(self, *args, **kwargs):
        super(StationXMLForm, self).__init__(*args, **kwargs)
        self.fields['stationxmlfile'].label = "Select file"


class ArchiveMonitoringInitForm(forms.ModelForm):
    class Meta:
        model = ArchiveMonitoring
        fields = "__all__"
        exclude = ('networks','components','stations','config',)


        YEAR_CHOICES = [(r,r) for r in range(datetime.date.today().year,1999-1,-1)]
        widgets = {
            'start_year': forms.Select(choices=YEAR_CHOICES),
            'end_year': forms.Select(choices=YEAR_CHOICES),
            }

    def __init__(self, *args, **kwargs):
        # This is to have a popover help for each fields
        super(ArchiveMonitoringInitForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            if help_text != '':
                self.fields[field].widget.attrs.update({'class':'has-popover', 'title':help_text, 'data-placement':'right', 'data-container':'body'})


    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_year")
        end_date = cleaned_data.get("end_year")

        if end_date and start_date:
            if end_date < start_date:
                msg = "End year should be greater than start year."
                self.add_error("end_year", msg)

class QCConfigInitForm(forms.ModelForm):
    class Meta:
        model = QCConfig
        fields = "__all__"


# class LoginForm(forms.Form):
#     user = forms.TextInput(label = "Email Address", required = True, max_length = 100,
#          widget = forms.TextInput(attrs = {'placeholder': 'Username', 'autocomplete':'off'}))
#     password = forms.CharField(label = "Password", required = True, max_length = 100,
#              widget = forms.PasswordInput(attrs = {'placeholder': 'Password', 'autocomplete':'off'}))
