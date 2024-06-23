from django import forms
from django.utils.timezone import datetime


class MonthYearForm(forms.Form):
    month = forms.ChoiceField(
        choices=[(i, i) for i in range(1, 13)], initial=datetime.now().month
    )
    year = forms.ChoiceField(
        choices=[(i, i) for i in range(2020, datetime.now().year + 1)],
        initial=datetime.now().year,
    )
