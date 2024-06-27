import base64
import csv
from datetime import datetime  # Correct import
from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render

from allianceauth.services.hooks import get_extension_logger

from .forms import ColumnMappingForm, CSVUploadForm, MonthYearForm
from .models import (
    CSVColumnMapping,
    IgnoredCSVColumns,
    MonthlyCreatorStats,
    MonthlyFleetType,
)
from .tasks import process_afat_data_task, process_csv_task

logger = get_extension_logger(__name__)

logger = get_extension_logger(__name__)


def upload_afat_data(request):
    if request.method == "POST":
        form = MonthYearForm(request.POST)
        if form.is_valid():
            month = form.cleaned_data["month"]
            year = form.cleaned_data["year"]

            # Trigger the Celery task
            process_afat_data_task.delay(month, year)
            return HttpResponse("AFAT data is being processed.")
    else:
        form = MonthYearForm()
    return render(request, "upload_afat_data.html", {"form": form})


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


def creator_charts(request):
    # Get month and year from request GET parameters, default to current month and year if not provided
    month = request.GET.get("month", datetime.now().month)
    year = request.GET.get("year", datetime.now().year)

    # Convert month and year to integers
    month = int(month)
    year = int(year)

    # Generate list of months and years for the dropdowns
    months = range(1, 13)
    current_year = datetime.now().year
    years = range(2023, current_year + 1)

    # Query data from MonthlyCreatorStats
    stats = MonthlyCreatorStats.objects.filter(month=month, year=year)
    fleet_types = MonthlyFleetType.objects.filter(source="afat")

    # Prepare data for the stacked bar chart
    creators = list(
        {stat.get_creator().profile.main_character.character_name for stat in stats}
    )
    data = {fleet_type.name: [0] * len(creators) for fleet_type in fleet_types}
    for stat in stats:
        if stat.fleet_type.source == "afat":
            creator_name = stat.get_creator().profile.main_character.character_name
            data[stat.fleet_type.name][
                creators.index(creator_name)
            ] += stat.total_created

    df = pd.DataFrame(data, index=creators)
    df = df.sort_index()  # Sort the DataFrame by the alphabetical name of the creators

    # Initialize base64 strings
    image_base64 = ""
    pie_image_base64 = ""

    if not df.empty:
        # Remove columns with all zeros
        df = df.loc[:, (df != 0).any(axis=0)]

        if not df.empty:
            # Create the stacked bar chart with colormap
            colormap = plt.cm.viridis  # Use a colormap like 'viridis'
            color_range = colormap(np.linspace(0, 1, len(df.columns)))

            plt.figure(figsize=(12, 8))
            df.plot(kind="bar", stacked=True, figsize=(12, 8), color=color_range)
            plt.xlabel("Creators")
            plt.ylabel("Total Created")
            plt.title(f"Fleet Types By FC for {month}/{year}")
            plt.xticks(rotation=45, ha="right")
            plt.legend(title="Fleet Type")
            plt.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
            plt.tight_layout()

            # Save the bar chart to a string buffer
            buf = BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            image_base64 = base64.b64encode(buf.read()).decode("utf-8")
            buf.close()
            plt.clf()

        # Prepare data for the pie chart
        total_created_by_fleet = (
            stats.filter(fleet_type__source="afat")
            .values("fleet_type__name")
            .annotate(total_created=Sum("total_created"))
            .order_by()
        )
        fleet_types = [item["fleet_type__name"] for item in total_created_by_fleet]
        proportions = [item["total_created"] for item in total_created_by_fleet]

        if proportions:
            # Create the pie chart with colormap
            pie_color_range = colormap(np.linspace(0, 1, len(fleet_types)))

            plt.figure(figsize=(8, 8))
            wedges, texts, autotexts = plt.pie(
                proportions,
                autopct="%1.1f%%",
                startangle=140,
                colors=pie_color_range,
            )
            plt.legend(
                wedges,
                fleet_types,
                title="Fleet Type",
                loc="center left",
                bbox_to_anchor=(1, 0, 0.5, 1),
            )
            plt.title(f"Fleet Type Proportions for {month}/{year}")
            plt.tight_layout()

            # Save the pie chart to a string buffer
            buf = BytesIO()
            plt.savefig(buf, format="png", bbox_inches="tight")
            buf.seek(0)
            pie_image_base64 = base64.b64encode(buf.read()).decode("utf-8")
            buf.close()
            plt.clf()

    return render(
        request,
        "charts/creator_charts.html",
        {
            "bar_chart": image_base64,
            "pie_chart": pie_image_base64,
            "month": month,
            "year": year,
            "months": months,
            "years": years,
        },
    )
