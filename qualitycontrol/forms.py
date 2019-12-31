# -*- coding: utf-8 -*-
from django import forms
from bootstrap_datepicker_plus import DateTimePickerInput
from .models import Metadata
from archive.models import NSLC


class GetMetadataForm(forms.Form):
    METHOD_CHOICES = (
        ("local_dir", 'Select local dir/'),
        ("web_service", 'Use a webservice'),
        ("svn", 'Use SVN'),
    )
    method = forms.MultipleChoiceField(widget=forms.Select,
                                       choices=METHOD_CHOICES)

class MetadataFolderForm(forms.Form):
    dir = forms.CharField(
        label='Select Directory',
        widget=forms.TextInput(attrs={'placeholder': '/path/to/metadata',
                                      'size': '30px',
                                      'title':'Will scan all directories '
                                      'and subdirectories to find metadata'})
        )


class MetadataWSForm(forms.Form):
    client = forms.CharField(
           label='Client address :',
           widget=forms.TextInput(
                 attrs={'placeholder':
                        'http://ws.ipgp.fr',
                        'size': '30',
                        }))

class MetadataSVNForm(forms.Form):
    svn_address = forms.CharField(
                label='SVN address :',
                widget=forms.TextInput(
                      attrs={'placeholder':
                             'https://svn.ipgp.fr/ovsm/trunk/dataless/stations/',
                             'size':'40',
                             'title':'Will scan all directories '
                             'and subdirectories to find metadatas'
                             }))
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput())


class MetadataForm(forms.Form):
    nslc_list = forms.ModelMultipleChoiceField(queryset=Metadata.objects.all(),
                                               widget=forms.SelectMultiple(
                                                     attrs={'size': 20}),
                                               label="Select channel(s)",
                                               )

class MetadataUniqueForm(forms.Form):
    nslc = forms.ModelChoiceField(queryset=Metadata.objects.all(),
                                  widget=forms.Select(
                                        attrs={'size': 16}),
                                  label="Select channel",
                                  )
    starttime = forms.DateTimeField(widget=DateTimePickerInput(
                                      attrs={'class': 'datetimepicker-input',
                                      'placeholder':'Not required'},
                                      format='YYYY-MM-DD HH:mm:ss'),
                                  label="Metadata Starttime",
                                  required = False)
    endtime = forms.DateTimeField(widget=DateTimePickerInput(
                                      attrs={'class': 'datetimepicker-input',
                                      'placeholder':'Not required'},
                                      format='YYYY-MM-DD HH:mm:ss'),
                                  label="Metadata Endtime",
                                  required = False)

class NSLCYearForm(forms.Form):
    nslc = forms.ModelChoiceField(queryset=NSLC.objects.all(),
                                  widget=forms.Select(
                                        attrs={'size': 20}),
                                  label="Select channel",
                                  )
    year = forms.DateField(input_formats=['%Y'],
                           widget = DateTimePickerInput(
                                  format='%Y',attrs={'size': 3}),
                           label="Select a year",)


class MetadataYearForm(forms.Form):
    nslc = forms.ModelChoiceField(queryset=Metadata.objects.all(),
                                  widget=forms.Select(
                                        attrs={'size': 17}),
                                  label="Select channel",
                                  )
    year = forms.DateField(input_formats=['%Y'],
                           widget=DateTimePickerInput(format='%Y'),
                           label="Select a year",)



class MetadataDatesForm(forms.Form):
    metadata_list = forms.ModelMultipleChoiceField(queryset=Metadata.objects.all(),
                                          widget=forms.SelectMultiple(
                                                attrs={'size': 16}),
                                          label="Select channel(s)",
                                          )
    starttime = forms.DateTimeField(widget=DateTimePickerInput(
                                      attrs={'class': 'datetimepicker-input',
                                      'placeholder':'Not required'},
                                      format='YYYY-MM-DD HH:mm:ss'),
                                    label="Metadata Starttime",
                                    required = False)
    endtime = forms.DateTimeField(widget=DateTimePickerInput(
                                      attrs={'class': 'datetimepicker-input',
                                      'placeholder':'Not required'},
                                      format='YYYY-MM-DD HH:mm:ss'),
                                  label="Metadata Endtime",
                                  required = False)


# class NewRequestForm(forms.ModelForm):
#     class Meta:
#         model = GapList
#         fields = ['nslc_list', 'starttime', 'endtime']
#         widgets = {'starttime': DateTimePickerInput(attrs={'class': 'datetimepicker-input',
#                                                             'placeholder':'Select a date',},
#                                                     format='YYYY-MM-DD HH:mm:ss'),
#                     'endtime': DateTimePickerInput(attrs={'class': 'datetimepicker-input',
#                                                           'placeholder':'Select a date'},
#                                                   format='YYYY-MM-DD HH:mm:ss'),
#                     }
#     def clean(self):
#         cleaned_data = super().clean()
#         start_date = cleaned_data.get("starttime")
#         end_date = cleaned_data.get("endtime")
#
#         if end_date and start_date:
#             if end_date < start_date:
#                 msg = "Endtime should be greater than starttime."
#                 self.add_error("endtime", msg)
