# views.py

import csv

from django.http import HttpResponse
from django.shortcuts import redirect, render

from allianceauth.services.hooks import get_extension_logger

from .forms import ColumnMappingForm, CSVUploadForm
from .models import CSVColumnMapping, IgnoredCSVColumns
from .tasks import process_csv_task

logger = get_extension_logger(__name__)


def upload_csv(request):
    if request.method == "POST":
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES["csv_file"]
            month = form.cleaned_data["month"]
            year = form.cleaned_data["year"]

            # Read CSV file to get columns
            decoded_file = csv_file.read().decode("utf-8").splitlines()
            reader = csv.reader(decoded_file)
            columns = next(reader)

            # Remove 'Account' column from columns to be mapped and filter out empty columns
            ignored_columns = IgnoredCSVColumns.objects.values_list(
                "column_name", flat=True
            )
            columns_to_map = [
                col.strip()
                for col in columns
                if col.strip()
                and col.strip() not in ignored_columns
                and col.strip() != "Account"
            ]

            # Fetch previous mappings
            previous_mappings = CSVColumnMapping.objects.all()
            initial_data = {}
            for mapping in previous_mappings:
                initial_data[mapping.column_name] = mapping.mapped_to
                initial_data[f"ignore_{mapping.column_name}"] = False

            for ignored in ignored_columns:
                initial_data[f"ignore_{ignored}"] = True

            # Render the column mapping form
            column_form = ColumnMappingForm(
                columns=columns_to_map, initial=initial_data
            )
            request.session["csv_data"] = decoded_file
            request.session["month"] = month
            request.session["year"] = year
            return render(
                request,
                "map_columns.html",
                {"form": column_form, "columns": columns_to_map},
            )
    else:
        form = CSVUploadForm()
    return render(request, "upload_csv.html", {"form": form})


def map_columns(request):
    if request.method == "POST":
        csv_data = request.session["csv_data"]
        month = request.session["month"]
        year = request.session["year"]
        columns_to_map = [
            col.strip()
            for col in csv_data[0].split(",")
            if col.strip() and col.strip() != "Account"
        ]
        form = ColumnMappingForm(request.POST, columns=columns_to_map)
        if form.is_valid():
            column_mapping = {}
            ignored_columns = []

            # Clear existing mappings
            CSVColumnMapping.objects.all().delete()

            for column in columns_to_map:
                if form.cleaned_data[f"ignore_{column}"]:
                    ignored_columns.append(column)
                    IgnoredCSVColumns.objects.get_or_create(column_name=column)
                elif form.cleaned_data[column]:
                    column_mapping[column] = form.cleaned_data[column]

            # Store column mappings in the database
            for column, mapped_to in column_mapping.items():
                CSVColumnMapping.objects.update_or_create(
                    column_name=column, defaults={"mapped_to": mapped_to}
                )

            process_csv_task.delay(csv_data, column_mapping, month, year)
            return HttpResponse("CSV is being processed.")
        else:
            logger.debug(f"Form errors: {form.errors}")
            logger.debug(f"Form data: {request.POST}")
    return redirect("upload_csv")
