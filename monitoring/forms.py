# -*- coding: utf-8 -*-
from django import forms
from .models import ArchiveMonitoring
import datetime

class ArchiveMonitoringForm(forms.ModelForm):
    class Meta:
        model = ArchiveMonitoring
        fields = "__all__"
        exclude = ('components','stations',)


        YEAR_CHOICES = [(r,r) for r in range(datetime.date.today().year,1999-1,-1)]
        widgets = {
            'networks': forms.widgets.CheckboxSelectMultiple(),
            # 'networks': forms.widgets.SelectMultiple(attrs={'size': Network.objects.count()}),
            # 'stations': forms.widgets.CheckboxSelectMultiple(),
            # 'sources': forms.widgets.CheckboxSelectMultiple(),
            'start_year': forms.Select(choices=YEAR_CHOICES),
            'end_year': forms.Select(choices=YEAR_CHOICES),
            }

    def __init__(self, *args, **kwargs):
        # This is to have a popover help for each fields
        super(ArchiveMonitoringForm, self).__init__(*args, **kwargs)
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
