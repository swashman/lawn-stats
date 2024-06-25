# forms.py

from datetime import datetime

from django import forms


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField()
    current_date = datetime.now()
    initial_month = current_date.month - 1 if current_date.month > 1 else 12
    initial_year = (
        current_date.year if current_date.month > 1 else current_date.year - 1
    )
    month = forms.IntegerField(initial=initial_month)
    year = forms.IntegerField(initial=initial_year)


class ColumnMappingForm(forms.Form):
    def __init__(self, *args, **kwargs):
        columns = kwargs.pop("columns")
        super().__init__(*args, **kwargs)
        for column in columns:
            self.fields[column] = forms.CharField(max_length=100, required=False)
            self.fields[f"ignore_{column}"] = forms.BooleanField(
                required=False, label="Ignore"
            )
