# -*- coding: utf-8 -*-
from django.contrib import admin
from django import forms
from .models import Metadata, LastUpdate, QCConfig

class MetadataAdmin(admin.ModelAdmin):
    list_display = ('get_code', 'file')
    list_filter = ("nslc__net","nslc__sta")
    def get_code(self, obj):
        return obj.nslc.code
    get_code.short_description = 'N.S.L.C.'
    get_code.admin_order_field = 'nslc__code'
    # Following method reduces the time to display the page
    def get_queryset(self, request):
        return super(MetadataAdmin,self).get_queryset(request).select_related('nslc')

    class Meta:
        ordering = ['-nslc__code']

class QCConfigForm(forms.ModelForm):
    class Meta:
        model = QCConfig
        fields = "__all__"

    def clean(self):
        if QCConfig.objects.exists() and not self.instance.pk:
            raise forms.ValidationError('There can be only 1 QC Configuration')

class QCConfigAdmin(admin.ModelAdmin):
    list_display = ('archive', 'metadata_format')
    form = QCConfigForm


admin.site.register(QCConfig,QCConfigAdmin)
admin.site.register(Metadata, MetadataAdmin)
admin.site.register(LastUpdate)
