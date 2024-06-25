# forms.py

from datetime import datetime

from django import forms


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={"class": "form-control"})
    )
    current_date = datetime.now()
    initial_month = current_date.month - 1 if current_date.month > 1 else 12
    initial_year = (
        current_date.year if current_date.month > 1 else current_date.year - 1
    )
    month = forms.IntegerField(
        initial=initial_month, widget=forms.NumberInput(attrs={"class": "form-control"})
    )
    year = forms.IntegerField(
        initial=initial_year, widget=forms.NumberInput(attrs={"class": "form-control"})
    )


class ColumnMappingForm(forms.Form):
    def __init__(self, *args, **kwargs):
        columns = kwargs.pop("columns")
        initial = kwargs.pop("initial", {})
        super().__init__(*args, **kwargs)
        for column in columns:
            self.fields[column] = forms.CharField(
                max_length=100,
                required=False,
                initial=initial.get(column),
                widget=forms.TextInput(
                    attrs={
                        "class": "form-control",
                        "placeholder": f"Map {column} to...",
                    }
                ),
                label=column,
            )
            self.fields[f"ignore_{column}"] = forms.BooleanField(
                required=False,
                label="Ignore",
                initial=initial.get(f"ignore_{column}", False),
                widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
            )


class MonthYearForm(forms.Form):
    month = forms.IntegerField(min_value=1, max_value=12, initial=datetime.now().month)
    year = forms.IntegerField(
        min_value=2000, max_value=datetime.now().year, initial=datetime.now().year
    )
