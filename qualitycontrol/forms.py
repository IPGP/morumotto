# -*- coding: utf-8 -*-
from django import forms
from bootstrap_datepicker_plus import DateTimePickerInput
from .models import Metadata


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
        widget=forms.TextInput(attrs={'placeholder': '/path/to/metadatas',
                                      })
        )


class MetadataWSForm(forms.Form):
    client = forms.CharField(
           label='Client address :',
           widget=forms.TextInput(
                 attrs={'placeholder':
                        'service.iris.edu/fdsnws/station/1/',
                        'size': '30'
                        }))

class MetadataSVNForm(forms.Form):
    svn_address = forms.CharField(
                label='SVN address :',
                widget=forms.TextInput(
                      attrs={'placeholder':
                             'https://svn.ipgp.fr/ovsm/trunk/dataless/stations/',
                             'size':'40'
                             }))
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput())


class NSLCForm(forms.Form):
    nslc_list = forms.ModelMultipleChoiceField(queryset=Metadata.objects.all(),
                                               widget=forms.SelectMultiple(
                                                     attrs={'size': 20}),
                                               label="Select station(s)",
                                               )

class NSLCUniqueForm(forms.Form):
    nslc = forms.ModelChoiceField(queryset=Metadata.objects.all(),
                                  widget=forms.Select(
                                        attrs={'size': 20}),
                                  label="Select station",
                                  )

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
