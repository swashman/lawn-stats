# views.py

import csv

from django.http import HttpResponse
from django.shortcuts import redirect, render

from allianceauth.services.hooks import get_extension_logger

from .forms import ColumnMappingForm, CSVUploadForm
from .models import CSVColumnMapping
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

            # Remove 'Account' column from columns to be mapped
            columns_to_map = [
                col.strip() for col in columns if col.strip() != "Account"
            ]

            # Log the columns to verify correct reading
            logger.debug(f"CSV columns: {columns_to_map}")

            # Render the column mapping form
            column_form = ColumnMappingForm(columns=columns_to_map)
            request.session["csv_data"] = decoded_file
            request.session["month"] = month
            request.session["year"] = year
            return render(request, "map_columns.html", {"form": column_form})
    else:
        form = CSVUploadForm()
    return render(request, "upload_csv.html", {"form": form})


def map_columns(request):
    if request.method == "POST":
        csv_data = request.session["csv_data"]
        month = request.session["month"]
        year = request.session["year"]
        columns_to_map = [
            col.strip() for col in csv_data[0].split(",") if col.strip() != "Account"
        ]
        form = ColumnMappingForm(request.POST, columns=columns_to_map)
        if form.is_valid():
            column_mapping = {
                column: form.cleaned_data[column] for column in form.fields
            }
            logger.debug(f"Initial column mapping: {column_mapping}")

            # Filter out empty mappings
            column_mapping = {
                column: mapped_to
                for column, mapped_to in column_mapping.items()
                if mapped_to
            }
            logger.debug(f"Filtered column mapping: {column_mapping}")

            # Store column mappings in the database
            for column, mapped_to in column_mapping.items():
                logger.debug(f"Storing column mapping: {column} -> {mapped_to}")
                CSVColumnMapping.objects.update_or_create(
                    column_name=column, defaults={"mapped_to": mapped_to}
                )

            process_csv_task.delay(csv_data, column_mapping, month, year)
            return HttpResponse("CSV is being processed.")
        else:
            logger.debug("Column mapping form is invalid")
            logger.debug(f"Form errors: {form.errors}")
            logger.debug(f"Form data: {request.POST}")
    return redirect("upload_csv")
