# -*- coding: utf-8 -*-
from django import forms
from seismicarchive.models import GapList, NSLC, Source, Configuration
from bootstrap_datepicker_plus import DateTimePickerInput


class SourceForm(forms.Form):
    source_list = forms.ModelMultipleChoiceField(
                queryset=Source.objects.all(),
                widget=forms.SelectMultiple(
                      attrs={'size': 9, 'style': 'width:100%;'}),
                      label="Select source(s)",
                      help_text="Leave empty if you want the request to ask all"
                      " sources configured for the given NSLC. "
                      "If you select source(s), the request will only ask "
                      "for these sources, ignioring others",
                     required = False,
                     # initial = [s for s in Source.objects.all() if Source.objects.all().count()], 
                     )


class WindowForm(forms.ModelForm):
    class Meta:
        model = Configuration
        fields = ['f_analysis', 'l_analysis', 'w_analysis', 'granularity_type']
        widgets = {
            'f_analysis': forms.NumberInput(attrs={'onchange':'update_value()'}),
            'w_analysis': forms.NumberInput(attrs={'onchange':'update_value()'}),
            'l_analysis': forms.NumberInput(attrs={'onchange':'update_value()'}),
            'granularity_type': forms.Select(attrs={'onchange':'update_value()'}),
            }
    def __init__(self, *args, **kwargs):
        # This is to have a popover help for each fields
        super(WindowForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            help_text = self.fields[field].help_text
            self.fields[field].help_text = None
            if help_text != '':
                self.fields[field].widget.attrs.update({'class':'has-popover',
                                                        'title':help_text,
                                                        'data-placement':'right',
                                                        'data-container':'body'})

    def clean(self):
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
        return self.cleaned_data



class NewRequestForm(forms.ModelForm):
    class Meta:
        model = GapList

        fields = ['nslc_list', 'starttime', 'endtime']
        widgets = {'starttime': DateTimePickerInput(attrs={'class': 'datetimepicker-input',
                                                            'placeholder':'Select a date',},
                                                    format='YYYY-MM-DD HH:mm:ss'),
                    'endtime': DateTimePickerInput(attrs={'class': 'datetimepicker-input',
                                                          'placeholder':'Select a date'},
                                                  format='YYYY-MM-DD HH:mm:ss'),
                    'nslc_list': forms.SelectMultiple(attrs={'size': 12}),
                    }
        labels = { "nslc_list": "Select NSLC(s)" }
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("starttime")
        end_date = cleaned_data.get("endtime")

        if end_date and start_date:
            if end_date < start_date:
                msg = "Endtime should be greater than starttime."
                self.add_error("endtime", msg)

# class NSLCForm(forms.Form):
#     nslc_list = forms.ModelMultipleChoiceField(queryset=Metadata.objects.all(),
#                                                widget=forms.SelectMultiple(
#                                                      attrs={'size': 20}),
#                                                label="Select NSLC(s)",
#                                                )
