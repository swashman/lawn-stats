import base64
import calendar
import csv
from collections import defaultdict
from datetime import datetime, timedelta  # Correct import
from io import BytesIO

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

from django.conf import settings
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render

from allianceauth.services.hooks import get_extension_logger

from .forms import ColumnMappingForm, CSVUploadForm, MonthYearForm
from .models import (
    AuthenticationUserprofile,
    CSVColumnMapping,
    EveonlineEveallianceinfo,
    EveonlineEvecorporationinfo,
    IgnoredCSVColumns,
    MonthlyCorpStats,
    MonthlyCreatorStats,
    MonthlyFleetType,
    MonthlyUserStats,
)
from .tasks import process_afat_data_task, process_csv_task

logger = get_extension_logger(__name__)

CHART_BACKGROUND_COLOR = "#575555"
months_to_display = 5


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
    return render(request, "lawn_stats/upload_afat_data.html", {"form": form})


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
                "lawn_stats/map_columns.html",
                {"form": column_form, "columns": columns_to_map},
            )
    else:
        form = CSVUploadForm()
    return render(request, "lawn_stats/upload_csv.html", {"form": form})


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


def get_default_month_and_year():
    current_date = datetime.now()
    first_of_this_month = current_date.replace(day=1)
    last_month_date = first_of_this_month - timedelta(days=1)
    return last_month_date.month, last_month_date.year


def all_charts(request):
    # Get month and year from request GET parameters, default to current month and year if not provided
    current_date = datetime.now()
    default_month, default_year = get_default_month_and_year()

    month = int(request.GET.get("month", default_month))
    year = int(request.GET.get("year", default_year))

    # Convert month and year to integers
    month = int(month)
    year = int(year)

    # Adjust month and year based on navigation buttons
    if "prev_month" in request.GET:
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    elif "next_month" in request.GET and (
        month < current_date.month or year < current_date.year
    ):
        month += 1
        if month == 13:
            month = 1
            year += 1
    elif "next_to_current" in request.GET:
        month = current_date.month
        year = current_date.year

    # Determine if forward navigation buttons should be shown
    show_forward = month < (current_date.month - 1) or year < current_date.year

    # List of month names for display
    month_names = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    # Fetch creator charts data
    creator_charts_data = creator_charts(month, year)
    logger.info("FC Chart completed")
    # fetch alliance charts data
    alliance_charts_data = alliance_charts(month, year)
    logger.info("Alliance Chart completed")
    # fetch corp charts data
    corp_charts_data = corp_charts(month, year)
    logger.info("Corp Chart completed")
    # fetch raw data
    raw_data_result = raw_data_view(month, year)
    logger.info("Raw Data completed")

    # Prepare context
    context = {
        "month": month,
        "year": year,
        "selected_month": month_names[month - 1],
        "selected_year": year,
        "creator_charts_data": creator_charts_data,
        "alliance_charts": alliance_charts_data,
        "corp_charts": corp_charts_data,
        "raw_data": raw_data_result.get("raw_data"),
        "top_afat_users": raw_data_result.get("top_afat_users"),
        "top_combined_users": raw_data_result.get("top_combined_users"),
        "show_forward": show_forward,
    }

    return render(request, "lawn_stats/base_charts.html", context)


def creator_charts(month, year):
    # Query data from MonthlyCreatorStats
    stats = MonthlyCreatorStats.objects.filter(month=month, year=year)
    fleet_types = MonthlyFleetType.objects.filter(source="afat", month=month, year=year)

    month_name = datetime(year, month, 1).strftime("%B")

    creators = set()
    for stat in stats:
        # Log the ID of the stat
        logger.info(f"Logging stat ID: {stat.creator_id}")

        # Check if main_character exists; otherwise, use username
        creator_name = (
            stat.get_creator().profile.main_character.character_name
            if stat.get_creator().profile.main_character
            else stat.get_creator().username
        )
        creators.add(creator_name)

    creators = list(creators)
    data = {fleet_type.name: [0] * len(creators) for fleet_type in fleet_types}
    for stat in stats:
        if stat.fleet_type.source == "afat":
            # Check if main_character exists; otherwise, use username
            creator_name = (
                stat.get_creator().profile.main_character.character_name
                if stat.get_creator().profile.main_character
                else stat.get_creator().username
            )
            data[stat.fleet_type.name][
                creators.index(creator_name)
            ] += stat.total_created

    df = pd.DataFrame(data, index=creators)
    df = df.sort_index()

    # Initialize base64 strings
    image_base64 = ""
    pie_image_base64 = ""
    line_chart_base64 = ""

    if not df.empty:
        # Remove columns with all zeros
        df = df.loc[:, (df != 0).any(axis=0)]

        if not df.empty:
            colormap = plt.cm.viridis
            color_range = colormap(np.linspace(0, 1, len(df.columns)))

            plt.figure(figsize=(12, 8))
            ax = df.plot(kind="bar", stacked=True, figsize=(12, 8), color=color_range)
            ax.set_facecolor(CHART_BACKGROUND_COLOR)
            plt.gcf().set_facecolor(CHART_BACKGROUND_COLOR)
            plt.ylabel("Total Created", color="lightgray")
            plt.title(
                f"Fleet Types By FC for {month_name} {year}",
                color="white",
                fontsize="16",
                fontweight="bold",
            )
            plt.xticks(rotation=45, ha="right", color="white")
            plt.yticks(color="white")
            plt.legend(
                facecolor="#2c2f33",
                edgecolor="white",
                title_fontsize="13",
                fontsize="11",
                labelcolor="lightgray",
            )
            plt.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
            ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True, prune="both"))
            plt.tight_layout()

            buf = BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            image_base64 = base64.b64encode(buf.read()).decode("utf-8")
            buf.close()
            plt.clf()
            plt.close()

        total_created_by_fleet = (
            stats.filter(fleet_type__source="afat")
            .values("fleet_type__name")
            .annotate(total_created=Sum("total_created"))
            .order_by("fleet_type__name")
        )
        fleet_types = [item["fleet_type__name"] for item in total_created_by_fleet]
        proportions = [item["total_created"] for item in total_created_by_fleet]

        if proportions:
            pie_color_range = colormap(np.linspace(0, 1, len(fleet_types)))

            plt.figure(figsize=(8, 8))
            wedges, texts, autotexts = plt.pie(
                proportions,
                autopct="%1.1f%%",
                startangle=140,
                colors=pie_color_range,
                pctdistance=0.85,
            )
            plt.setp(texts, color="white")
            plt.setp(autotexts, color="black")
            plt.gcf().set_facecolor(CHART_BACKGROUND_COLOR)
            plt.legend(
                wedges,
                fleet_types,
                loc="center left",
                bbox_to_anchor=(1, 0, 0.5, 1),
                facecolor="#2c2f33",
                edgecolor="white",
                title_fontsize="13",
                fontsize="11",
                labelcolor="lightgray",
            )
            plt.title(
                f"Fleet Type Proportions for {month_name} {year}",
                color="white",
                fontsize="16",
                fontweight="bold",
            )
            plt.tight_layout()

            buf = BytesIO()
            plt.savefig(buf, format="png", bbox_inches="tight")
            buf.seek(0)
            pie_image_base64 = base64.b64encode(buf.read()).decode("utf-8")
            buf.close()
            plt.clf()
            plt.close()

    # Line chart for total fleets of each type each month
    start_month = (month - months_to_display) % 12 or 12
    start_year = year if month >= months_to_display else year - 1
    date_range = [
        (start_year + (start_month + i - 1) // 12, (start_month + i - 1) % 12 + 1)
        for i in range(months_to_display + 1)
    ]

    monthly_totals = (
        MonthlyCreatorStats.objects.filter(
            year__in=[start_year, year],
            month__in=[date[1] for date in date_range],
        )
        .values("month", "year", "fleet_type__name")
        .annotate(total_fleets=Sum("total_created"))
        .order_by("year", "month", "fleet_type__name")
    )

    fleet_type_names = {item["fleet_type__name"] for item in monthly_totals}
    line_data = {name: [0] * len(date_range) for name in fleet_type_names}
    for item in monthly_totals:
        fleet_name = item["fleet_type__name"]
        date_index = next(
            (
                i
                for i, date in enumerate(date_range)
                if date[1] == item["month"] and date[0] == item["year"]
            ),
            None,
        )
        if date_index is not None:
            line_data[fleet_name][date_index] = item["total_fleets"]

    if line_data:
        plt.figure(figsize=(12, 8))
        colors = plt.cm.viridis(np.linspace(0, 1, len(line_data)))  # Use colormap

        for (fleet_name, totals), color in zip(line_data.items(), colors):
            plt.plot(
                range(1, len(date_range) + 1),
                totals,
                marker="o",
                label=fleet_name,
                color=color,
            )

        plt.gcf().set_facecolor(CHART_BACKGROUND_COLOR)
        ax = plt.gca()
        ax.set_facecolor(CHART_BACKGROUND_COLOR)  # Set plot area background color
        plt.title(
            f"Month Over Month Fleet Types for {year}",
            color="white",
            fontsize=16,
            fontweight="bold",
        )
        plt.ylabel("Total Fleets", color="white")
        plt.xticks(
            ticks=range(1, len(date_range) + 1),
            labels=[f"{calendar.month_abbr[date[1]]} {date[0]}" for date in date_range],
            color="white",
            rotation=45,  # Set rotation for the labels
            ha="right",  # Align labels to the right
        )
        plt.yticks(color="white")
        plt.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
        plt.legend(
            loc="upper left",
            facecolor="#2c2f33",
            edgecolor="white",
            labelcolor="lightgray",
        )
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        line_chart_base64 = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()
        plt.clf()
        plt.close()

    return {
        "bar_chart": image_base64,
        "pie_chart": pie_image_base64,
        "line_chart": line_chart_base64,
    }


def alliance_charts(month, year):
    try:
        ally = EveonlineEveallianceinfo.objects.get(
            alliance_id=settings.STATS_ALLIANCE_ID
        )
        all_corps = (
            EveonlineEvecorporationinfo.objects.filter(alliance=ally)
            .exclude(corporation_id__in=settings.STATS_IGNORE_CORPS)
            .order_by("corporation_ticker")
        )
        corp_names = list(all_corps.values_list("corporation_ticker", flat=True))
    except EveonlineEveallianceinfo.DoesNotExist:
        corp_names = []

    stats = MonthlyCorpStats.objects.filter(
        month=month,
        year=year,
        corporation_id__in=all_corps.values_list("corporation_id", flat=True),
    ).select_related("fleet_type")

    data_afat = {}
    for corp in corp_names:
        logger.info("Corp: %s", corp)
        data_afat[corp] = {
            ft.name: 0
            for ft in MonthlyFleetType.objects.filter(
                month=month, year=year, source="afat"
            )
        }
    data_imp = {
        corp: {
            ft.name: 0
            for ft in MonthlyFleetType.objects.filter(
                month=month, year=year, source="imp"
            )
        }
        for corp in corp_names
    }

    relative_data = {corp: {"AFAT": 0, "IMP": 0} for corp in corp_names}

    for stat in stats:
        corp_ticker = stat.get_corporation().corporation_ticker
        logger.info(
            "Processing: corp- %s source- %s total- %s",
            corp_ticker,
            stat.fleet_type.source,
            stat.total_fats,
        )
        # total_mains = CorpStats.objects.get(corp=stat.get_corporation().pk).main_count
        corp_members = AuthenticationUserprofile.objects.filter(
            main_character__corporation_id=stat.get_corporation().corporation_id
        ).order_by("main_character__character_name")
        total_mains = corp_members.count()

        if stat.fleet_type.source == "afat":
            if corp_ticker in data_afat:  # Check if corp_ticker is in data_afat
                data_afat[corp_ticker][stat.fleet_type.name] += stat.total_fats
                if total_mains > 0:
                    relative_data[corp_ticker]["AFAT"] += stat.total_fats / total_mains
            else:
                logger.warning(
                    f"Ticker {corp_ticker} not found in data_afat, skipping stat."
                )

        elif stat.fleet_type.source == "imp":
            if corp_ticker in data_imp:  # Check if corp_ticker is in data_imp
                data_imp[corp_ticker][stat.fleet_type.name] += stat.total_fats
                if total_mains > 0:
                    relative_data[corp_ticker]["IMP"] += stat.total_fats / total_mains
            else:
                logger.warning(
                    f"Ticker {corp_ticker} not found in data_imp, skipping stat."
                )

    df_afat = pd.DataFrame(data_afat).T.fillna(0)
    df_imp = pd.DataFrame(data_imp).T.fillna(0)

    # Filter out columns with zero sums
    df_afat = df_afat.loc[:, (df_afat.sum(axis=0) != 0)]
    df_imp = df_imp.loc[:, (df_imp.sum(axis=0) != 0)]

    # Relative participation chart
    df_relative = pd.DataFrame(relative_data).T.fillna(0)

    x = np.arange(len(corp_names))

    # AFAT chart
    fig, ax = plt.subplots(figsize=(12.8, 8))
    fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.set_facecolor(CHART_BACKGROUND_COLOR)
    bottom_afat = np.zeros(len(corp_names))
    color_range_afat = plt.cm.viridis(np.linspace(0, 1, len(df_afat.columns)))

    for idx, column in enumerate(df_afat.columns):
        ax.bar(
            x,
            df_afat[column],
            bottom=bottom_afat,
            color=color_range_afat[idx],
            label=column,
        )
        bottom_afat += df_afat[column]

    for i, total in enumerate(bottom_afat):
        ax.text(
            i,
            total,
            f"{int(total)}",
            ha="center",
            va="bottom",
            color="white",
            fontsize=10,
        )

    ax.set_title(
        f"LAWN Fleet Breakdown for {calendar.month_name[month]} {year}",
        color="white",
        fontsize=16,
        fontweight="bold",
    )
    ax.set_ylabel("Total Fats", color="lightgray")
    ax.set_xticks(ticks=x)
    ax.set_xticklabels(corp_names, rotation=45, ha="right", color="white")
    ax.tick_params(axis="y", colors="lightgray")
    ax.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
    ax.legend(facecolor="#2c2f33", edgecolor="white", labelcolor="lightgray")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    afat_chart = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.clf()
    plt.close(fig)

    # IMP chart
    fig, ax = plt.subplots(figsize=(12.8, 8))
    fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.set_facecolor(CHART_BACKGROUND_COLOR)
    bottom_imp = np.zeros(len(corp_names))
    color_range_imp = plt.cm.winter(np.linspace(0, 1, len(df_imp.columns)))

    for idx, column in enumerate(df_imp.columns):
        ax.bar(
            x,
            df_imp[column],
            bottom=bottom_imp,
            color=color_range_imp[idx],
            label=column,
        )
        bottom_imp += df_imp[column]

    for i, total in enumerate(bottom_imp):
        ax.text(
            i,
            total,
            f"{int(total)}",
            ha="center",
            va="bottom",
            color="white",
            fontsize=10,
        )

    ax.set_title(
        f"IMPERIUM Fleet Breakdown for {calendar.month_name[month]} {year}",
        color="white",
        fontsize=16,
        fontweight="bold",
    )
    ax.set_ylabel("Total Paps", color="lightgray")
    ax.set_xticks(ticks=x)
    ax.set_xticklabels(corp_names, rotation=45, ha="right", color="white")
    ax.tick_params(axis="y", colors="lightgray")
    ax.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
    ax.legend(facecolor="#2c2f33", edgecolor="white", labelcolor="lightgray")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    imp_chart = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.clf()
    plt.close(fig)

    # Combined chart
    total_afat = df_afat.sum(axis=1)
    total_imp = df_imp.sum(axis=1)

    fig, ax = plt.subplots(figsize=(12.8, 8))
    fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.set_facecolor(CHART_BACKGROUND_COLOR)

    ax.bar(x - 0.2, total_afat, width=0.4, label="LAWN", color="cyan")
    ax.bar(x + 0.2, total_imp, width=0.4, label="IMP", color="blue")

    for i in range(len(corp_names)):
        ax.text(
            i - 0.2,
            total_afat.iloc[i],
            f"{int(total_afat.iloc[i])}",
            ha="center",
            va="bottom",
            color="white",
        )
        ax.text(
            i + 0.2,
            total_imp.iloc[i],
            f"{int(total_imp.iloc[i])}",
            ha="center",
            va="bottom",
            color="white",
        )

    ax.set_title(
        f"Fleet Participation for {calendar.month_name[month]} {year}",
        color="white",
        fontsize=16,
        fontweight="bold",
    )
    ax.set_ylabel("Total Fats", color="lightgray")
    ax.set_xticks(ticks=x)
    ax.set_xticklabels(corp_names, rotation=45, ha="right", color="white")
    ax.tick_params(axis="y", colors="lightgray")
    ax.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
    ax.legend(facecolor="#2c2f33", edgecolor="white", labelcolor="lightgray")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    combined_chart = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.clf()
    plt.close(fig)

    # Pie chart for AFAT fleet type proportions
    afat_totals = df_afat.sum(axis=0)
    fig, ax = plt.subplots(figsize=(8, 8))
    fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.set_facecolor(CHART_BACKGROUND_COLOR)
    wedges, texts, autotexts = ax.pie(
        afat_totals,
        autopct=lambda p: f"{p:.1f}%" if p > 1 else "",
        startangle=140,
        colors=color_range_afat,
        pctdistance=0.85,  # Adjust this value to move the labels further out
    )
    plt.setp(texts, color="white")
    plt.setp(autotexts, color="black")  # Set autopct text color
    ax.set_title(
        f"Fleet Type Participation for {calendar.month_name[month]} {year}",
        color="white",
        fontsize=16,
        fontweight="bold",
    )
    ax.legend(
        wedges,
        afat_totals.index,
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
        facecolor="#2c2f33",
        edgecolor="white",
        title_fontsize="13",
        fontsize="11",
        labelcolor="lightgray",
    )
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    pie_chart = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.clf()
    plt.close(fig)

    # Line chart for month over month AFAT data
    afat_stats = (
        MonthlyCorpStats.objects.filter(
            corporation_id__in=all_corps.values_list("corporation_id", flat=True),
            fleet_type__source="afat",
        )
        .values("year", "month")
        .annotate(total=Sum("total_fats"))
        .order_by("year", "month")
    )

    start_month = (month - months_to_display) % 12 or 12
    start_year = year if month > months_to_display else year - 1
    date_range = [
        (start_year + (start_month + i - 1) // 12, (start_month + i - 1) % 12 + 1)
        for i in range(months_to_display + 1)  # Include current month
    ]

    date_totals = {date: 0 for date in date_range}
    for item in afat_stats:
        date_totals[(item["year"], item["month"])] = item["total"]

    dates = [
        datetime(year=year, month=month, day=1) for year, month in date_totals.keys()
    ]
    totals = list(date_totals.values())

    # Calculate the running average
    running_avg = pd.Series(totals).rolling(window=3, min_periods=1).mean()

    fig, ax = plt.subplots(figsize=(12.8, 8))
    fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.plot(dates, totals, marker="o", color="cyan", label="Total Fats")
    ax.plot(dates, running_avg, linestyle="--", color="orange", label="Running Average")
    # Annotate the total for each month

    for i, total in enumerate(totals):
        if total > 0:
            ax.text(
                dates[i],
                total + 5,
                f"{total}",
                ha="center",
                va="bottom",
                color="white",
                fontsize=10,
            )

    ax.set_title(
        "Month Over Month Lawn Fats", color="white", fontsize=16, fontweight="bold"
    )
    ax.set_ylabel("Total Fats", color="lightgray")
    ax.tick_params(axis="y", colors="lightgray")
    ax.tick_params(axis="x", colors="lightgray", rotation=45)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
    ax.legend(facecolor="#2c2f33", edgecolor="white", labelcolor="lightgray")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    line_chart = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.clf()
    plt.close(fig)

    # Relative participation chart
    fig, ax = plt.subplots(figsize=(12.8, 8))
    fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
    ax.set_facecolor(CHART_BACKGROUND_COLOR)

    bar_afat = ax.bar(
        x - 0.2, df_relative["AFAT"], width=0.4, label="LAWN", color="cyan"
    )
    bar_imp = ax.bar(x + 0.2, df_relative["IMP"], width=0.4, label="IMP", color="blue")

    for bar in bar_afat:
        yval = bar.get_height()
        if yval > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                yval,
                f"{yval:.1f}",
                ha="center",
                va="bottom",
                color="white",
            )

    for bar in bar_imp:
        yval = bar.get_height()
        if yval > 0:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                yval,
                f"{yval:.1f}",
                ha="center",
                va="bottom",
                color="white",
            )

    ax.set_title(
        f"Relative Participation(Fleets/Main) for {calendar.month_name[month]} {year}",
        color="white",
        fontsize=16,
        fontweight="bold",
    )
    ax.set_ylabel("Relative Participation", color="lightgray")
    ax.set_xticks(ticks=x)
    ax.set_xticklabels(corp_names, rotation=45, ha="right", color="white")
    ax.tick_params(axis="y", colors="lightgray")
    ax.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
    ax.legend(facecolor="#2c2f33", edgecolor="white", labelcolor="lightgray")
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    relative_chart = base64.b64encode(buf.read()).decode("utf-8")
    buf.close()
    plt.clf()
    plt.close(fig)

    return {
        "afat_chart": afat_chart,
        "imp_chart": imp_chart,
        "combined_chart": combined_chart,
        "pie_chart": pie_chart,
        "line_chart": line_chart,
        "relative_chart": relative_chart,
    }


def corp_charts(month, year):
    ally = EveonlineEveallianceinfo.objects.get(alliance_id=settings.STATS_ALLIANCE_ID)
    all_corps = (
        EveonlineEvecorporationinfo.objects.filter(alliance=ally)
        .exclude(corporation_id__in=settings.STATS_IGNORE_CORPS)
        .order_by("corporation_name")
    )

    charts_data = {}

    for corp in all_corps:
        corp_members = AuthenticationUserprofile.objects.filter(
            main_character__corporation_id=corp.corporation_id
        ).order_by("main_character__character_name")

        users = [member.main_character.character_name for member in corp_members]
        user_ids = [member.user_id for member in corp_members]

        stats = MonthlyUserStats.objects.filter(
            user_id__in=user_ids, month=month, year=year
        ).select_related("fleet_type")

        data_afat = {
            user: {
                ft.name: 0
                for ft in MonthlyFleetType.objects.filter(
                    source="afat", month=month, year=year
                )
            }
            for user in users
        }
        data_imp = {
            user: {
                f"IMP {ft.name}": 0
                for ft in MonthlyFleetType.objects.filter(
                    source="imp", month=month, year=year
                )
            }
            for user in users
        }

        for stat in stats:
            character_name = stat.get_user().profile.main_character.character_name
            if stat.fleet_type.source == "afat":
                data_afat[character_name][stat.fleet_type.name] += stat.total_fats
            elif stat.fleet_type.source == "imp":
                data_imp[character_name][
                    f"IMP {stat.fleet_type.name}"
                ] += stat.total_fats

        df_afat = pd.DataFrame(data_afat).T
        df_imp = pd.DataFrame(data_imp).T

        df_afat = df_afat.loc[:, (df_afat != 0).any(axis=0)]
        df_imp = df_imp.loc[:, (df_imp != 0).any(axis=0)]

        if not df_afat.empty or not df_imp.empty:
            fig, ax = plt.subplots(figsize=(12, 8))
            fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
            ax.set_facecolor(CHART_BACKGROUND_COLOR)

            bar_width = 0.35
            indices = np.arange(len(users))

            bottom_afat = np.zeros(len(users))
            bottom_imp = np.zeros(len(users))
            colors_afat = plt.cm.viridis(np.linspace(0, 1, len(df_afat.columns)))
            colors_imp = plt.cm.cool(np.linspace(0, 1, len(df_imp.columns)))

            for idx, column in enumerate(df_afat.columns):
                ax.bar(
                    indices - bar_width / 2,
                    df_afat[column].values,
                    bar_width,
                    bottom=bottom_afat,
                    color=colors_afat[idx],
                    label=column,
                )
                bottom_afat += df_afat[column].values

            for idx, column in enumerate(df_imp.columns):
                ax.bar(
                    indices + bar_width / 2,
                    df_imp[column].values,
                    bar_width,
                    bottom=bottom_imp,
                    color=colors_imp[idx],
                    label=column,
                )
                bottom_imp += df_imp[column].values

            ylim_bottom, ylim_top = ax.get_ylim()
            if ylim_top < 5:
                ax.set_ylim(0, 5)
            else:
                max_y = max(bottom_afat.max(), bottom_imp.max())
                ax.set_ylim(0, max_y * 1.1)

            for i, total in enumerate(bottom_afat):
                if total > 0:
                    ax.text(
                        i - bar_width / 2,
                        total,
                        f"{int(total)}",
                        ha="center",
                        va="bottom",
                        color="white",
                    )

            for i, total in enumerate(bottom_imp):
                if total > 0:
                    ax.text(
                        i + bar_width / 2,
                        total,
                        f"{int(total)}",
                        ha="center",
                        va="bottom",
                        color="white",
                    )

            ax.set_title(
                f"{corp.corporation_name} Fleet Breakdown for {calendar.month_name[month]} {year}",
                color="white",
                fontsize=16,
                fontweight="bold",
            )
            ax.set_ylabel("Total Fats", color="white")
            ax.set_xticks(indices)
            ax.set_xticklabels(users, rotation=45, ha="right", color="white")
            ax.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
            ax.tick_params(axis="y", colors="lightgray")
            ax.legend(facecolor="#2c2f33", edgecolor="white", labelcolor="lightgray")
            plt.tight_layout()

            buf = BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            charts_data[corp.corporation_name] = base64.b64encode(buf.read()).decode(
                "utf-8"
            )
            buf.close()
            plt.clf()
            plt.close()
        else:
            # Placeholder chart for corporations with no fats
            fig, ax = plt.subplots(figsize=(12, 8))
            fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
            ax.set_facecolor(CHART_BACKGROUND_COLOR)

            ax.text(
                0.5,
                0.5,
                "No Fats Data Available",
                ha="center",
                va="center",
                color="white",
                fontsize=16,
            )
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(
                f"{corp.corporation_name} Fleet Breakdown for {calendar.month_name[month]} {year}",
                color="white",
            )
            plt.tight_layout()

            buf = BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            charts_data[corp.corporation_name] = base64.b64encode(buf.read()).decode(
                "utf-8"
            )
            buf.close()
            plt.clf()
            plt.close()

        # Line chart for month over month AFAT and IMP data for each corp
        afat_stats = (
            MonthlyCorpStats.objects.filter(
                corporation_id=corp.corporation_id,
                fleet_type__source="afat",
            )
            .values("year", "month")
            .annotate(total=Sum("total_fats"))
            .order_by("year", "month")
        )

        imp_stats = (
            MonthlyCorpStats.objects.filter(
                corporation_id=corp.corporation_id,
                fleet_type__source="imp",
            )
            .values("year", "month")
            .annotate(total=Sum("total_fats"))
            .order_by("year", "month")
        )

        start_month = (month - months_to_display) % 12 or 12
        start_year = year if month >= months_to_display else year - 1
        date_range = [
            (start_year + (start_month + i - 1) // 12, (start_month + i - 1) % 12 + 1)
            for i in range(months_to_display + 1)
        ]
        date_totals_afat = {date: 0 for date in date_range}
        date_totals_imp = {date: 0 for date in date_range}
        for item in afat_stats:
            date_totals_afat[(item["year"], item["month"])] = item["total"]
        for item in imp_stats:
            date_totals_imp[(item["year"], item["month"])] = item["total"]

        # Ensure both lists are the same length by aligning data
        dates = [datetime(year=year, month=month, day=1) for year, month in date_range]
        totals_afat = [
            date_totals_afat.get((date.year, date.month), 0) for date in dates
        ]
        totals_imp = [date_totals_imp.get((date.year, date.month), 0) for date in dates]

        running_avg_afat = (
            pd.Series(totals_afat).rolling(window=3, min_periods=1).mean()
        )
        running_avg_imp = pd.Series(totals_imp).rolling(window=3, min_periods=1).mean()

        fig, ax = plt.subplots(figsize=(12, 8))
        fig.patch.set_facecolor(CHART_BACKGROUND_COLOR)
        ax.set_facecolor(CHART_BACKGROUND_COLOR)
        ax.plot(dates, totals_afat, marker="o", color="cyan", label="Total Fats")
        ax.plot(
            dates,
            running_avg_afat,
            linestyle="--",
            color="orange",
            label="Running Avg",
        )
        ax.plot(dates, totals_imp, marker="o", color="blue", label="IMP Total Fats")
        ax.plot(
            dates,
            running_avg_imp,
            linestyle="--",
            color="purple",
            label="IMP Running Avg",
        )

        for i, total in enumerate(totals_afat):
            if total > 0:
                ax.text(
                    dates[i],
                    total,
                    f"{total}",
                    ha="center",
                    va="bottom",
                    color="white",
                    fontsize=10,
                )

        for i, total in enumerate(totals_imp):
            if total > 0:
                ax.text(
                    dates[i],
                    total,
                    f"{total}",
                    ha="center",
                    va="bottom",
                    color="white",
                    fontsize=10,
                )

        ax.set_ylim(0)  # Ensure y-axis starts at zero
        ax.yaxis.get_major_locator().set_params(
            integer=True
        )  # Display only integer ticks
        ax.set_title(
            f"{corp.corporation_name} Month Over Month",
            color="white",
            fontsize=16,
            fontweight="bold",
        )
        ax.set_ylabel("Total Fats", color="lightgray")
        ax.tick_params(axis="y", colors="lightgray")
        ax.tick_params(axis="x", colors="lightgray", rotation=45)
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.grid(axis="y", linestyle="--", linewidth=0.5, color="grey", alpha=0.7)
        ax.legend(facecolor="#2c2f33", edgecolor="white", labelcolor="lightgray")
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        charts_data[f"{corp.corporation_name}_line"] = base64.b64encode(
            buf.read()
        ).decode("utf-8")
        buf.close()
        plt.clf()
        plt.close()

    return charts_data


def raw_data_view(month, year):
    raw_data = {}
    top_afat_users = []
    top_combined_users = []

    try:
        ally = EveonlineEveallianceinfo.objects.get(
            alliance_id=settings.STATS_ALLIANCE_ID
        )
    except EveonlineEveallianceinfo.DoesNotExist:
        return raw_data

    all_corps = (
        EveonlineEvecorporationinfo.objects.filter(alliance=ally)
        .exclude(corporation_id__in=settings.STATS_IGNORE_CORPS)
        .order_by("corporation_name")
    )

    user_data = []

    for corp in all_corps:
        corp_members = AuthenticationUserprofile.objects.filter(
            main_character__corporation_id=corp.corporation_id
        ).order_by("main_character__character_name")

        main_to_data = defaultdict(lambda: {"afat_total": 0, "imp_total": 0})

        for member in corp_members:
            user_id = member.user_id
            main_character = member.main_character.character_name

            afat_total = (
                MonthlyUserStats.objects.filter(
                    user_id=user_id, fleet_type__source="afat", month=month, year=year
                ).aggregate(total=Sum("total_fats"))["total"]
                or 0
            )

            imp_total = (
                MonthlyUserStats.objects.filter(
                    user_id=user_id, fleet_type__source="imp", month=month, year=year
                ).aggregate(total=Sum("total_fats"))["total"]
                or 0
            )

            main_to_data[main_character]["afat_total"] += afat_total
            main_to_data[main_character]["imp_total"] += imp_total

            # Collect user data for top 5 calculations
            user_data.append(
                {
                    "name": main_character,
                    "afat_total": afat_total,
                    "combined_total": afat_total + imp_total,
                }
            )

        corp_data = sorted(
            [
                {
                    "name": main,
                    "afat_total": data["afat_total"],
                    "imp_total": data["imp_total"],
                }
                for main, data in main_to_data.items()
            ],
            key=lambda x: x["name"],
        )

        raw_data[corp.corporation_name] = corp_data

    # Sort the user data and get top 5
    top_afat_users = sorted(user_data, key=lambda x: x["afat_total"], reverse=True)[:5]
    top_combined_users = sorted(
        user_data, key=lambda x: x["combined_total"], reverse=True
    )[:5]

    return {
        "raw_data": raw_data,
        "top_afat_users": top_afat_users,
        "top_combined_users": top_combined_users,
    }
