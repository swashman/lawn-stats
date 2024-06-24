import base64
import io
import urllib
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from django.core.files.storage import FileSystemStorage
from django.shortcuts import render

from .data_processing import (
    get_fats_by_type_for_members,
    get_monthly_totals_by_corporation,
    get_total_fats_by_corporation,
    import_csv_to_model,
)
from .forms import MonthYearForm
from .models import EveonlineEveallianceinfo, EveonlineEvecorporationinfo

ALLIANCE_ID = 150097440


def plot_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    buf.seek(0)
    string = base64.b64encode(buf.read())
    uri = urllib.parse.quote(string)
    return uri


def add_labels(ax):
    for p in ax.patches:
        ax.annotate(
            f"{p.get_height()}",
            (p.get_x() + p.get_width() / 2.0, p.get_height()),
            ha="center",
            va="center",
            xytext=(0, 10),
            textcoords="offset points",
        )


def get_last_9_months():
    now = datetime.now()
    months = []
    for i in range(9):
        month = (now - timedelta(days=i * 30)).strftime("%B - %Y")
        months.append(month)
    months.reverse()
    return months


def index(request):
    return render(request, "index.html")


def total_fats_chart(request):
    if request.method == "POST":
        form = MonthYearForm(request.POST)
        if form.is_valid():
            month = form.cleaned_data["month"]
            year = form.cleaned_data["year"]
    else:
        form = MonthYearForm()
        month = form.fields["month"].initial
        year = form.fields["year"].initial

    corp_totals = get_total_fats_by_corporation(month, year)

    # Get all corporations in the alliance using the provided method
    try:
        ally = EveonlineEveallianceinfo.objects.get(alliance_id=ALLIANCE_ID)
        all_corps = (
            EveonlineEvecorporationinfo.objects.filter(alliance=ally)
            .order_by("corporation_name")
            .values_list("corporation_name", flat=True)
        )
        all_corps_list = list(all_corps)  # Convert queryset to list
    except EveonlineEveallianceinfo.DoesNotExist:
        all_corps_list = []

    corp_totals_dict = dict(corp_totals)

    # Ensure all corporations are represented, even with 0 values
    final_corp_totals = [
        (corp, corp_totals_dict.get(corp, 0)) for corp in sorted(all_corps_list)
    ]

    fig, ax = plt.subplots(figsize=(10, 6))  # Rectangular size
    corporations = [corp_name for corp_name, _ in final_corp_totals]
    totals = [total_fats for _, total_fats in final_corp_totals]
    ax.bar(
        corporations, totals, color=plt.cm.rainbow(np.linspace(0, 1, len(corporations)))
    )
    ax.set_title(f"Total Fats by Corporation for {month}-{year}")
    ax.set_xlabel("Corporations")
    ax.set_ylabel("Total Fats")
    add_labels(ax)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    chart = plot_to_base64(fig)
    return render(
        request,
        "chart.html",
        {
            "chart": chart,
            "title": f"Total Fats by Corporation for {month}-{year}",
            "form": form,
        },
    )


def relative_participation_chart(request):
    if request.method == "POST":
        form = MonthYearForm(request.POST)
        if form.is_valid():
            month = form.cleaned_data["month"]
            year = form.cleaned_data["year"]
    else:
        form = MonthYearForm()
        month = form.fields["month"].initial
        year = form.fields["year"].initial

    corp_totals = get_total_fats_by_corporation(month, year)

    # Get all corporations in the alliance using the provided method
    try:
        ally = EveonlineEveallianceinfo.objects.get(alliance_id=ALLIANCE_ID)
        all_corps = (
            EveonlineEvecorporationinfo.objects.filter(alliance=ally)
            .order_by("corporation_name")
            .values_list("corporation_name", flat=True)
        )
        all_corps_list = list(all_corps)  # Convert queryset to list
    except EveonlineEveallianceinfo.DoesNotExist:
        all_corps_list = []

    corp_totals_dict = dict(corp_totals)

    # Ensure all corporations are represented, even with 0 values
    final_corp_totals = [
        (corp, corp_totals_dict.get(corp, 0)) for corp in sorted(all_corps_list)
    ]

    total_mains = 3  # Example value; adjust as needed
    relative_participation = {
        corp_name: round(total_fats / total_mains, 1)
        for corp_name, total_fats in final_corp_totals
    }

    fig, ax = plt.subplots(figsize=(10, 6))  # Rectangular size
    corporations = list(relative_participation.keys())
    participation = list(relative_participation.values())
    ax.bar(
        corporations,
        participation,
        color=plt.cm.rainbow(np.linspace(0, 1, len(corporations))),
    )
    ax.set_title(f"Relative Participation by Corporation for {month}-{year}")
    ax.set_xlabel("Corporations")
    ax.set_ylabel("Relative Participation")
    add_labels(ax)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    chart = plot_to_base64(fig)
    return render(
        request,
        "chart.html",
        {
            "chart": chart,
            "title": f"Relative Participation by Corporation for {month}-{year}",
            "form": form,
        },
    )


def monthly_totals_chart(request):
    if request.method == "POST":
        form = MonthYearForm(request.POST)
        if form.is_valid():
            form.cleaned_data["month"]
            form.cleaned_data["year"]
    else:
        form = MonthYearForm()
        form.fields["month"].initial
        form.fields["year"].initial

    monthly_totals = get_monthly_totals_by_corporation()
    corp_names = monthly_totals.values_list(
        "character__corporation_name", flat=True
    ).distinct()

    charts = []
    last_9_months = get_last_9_months()
    month_year_list = [
        (datetime.now() - timedelta(days=i * 30)).strftime("%Y-%m") for i in range(9)
    ]
    month_year_list.reverse()

    for corp_name in corp_names:
        fig, ax = plt.subplots(figsize=(10, 6))  # Rectangular size
        corp_data = monthly_totals.filter(character__corporation_name=corp_name)
        totals_by_month = {month: 0 for month in month_year_list}
        for total in corp_data:
            month_year = f"{total['year']}-{total['month']:02d}"
            if month_year in totals_by_month:
                totals_by_month[month_year] = total["total_fats"]

        months = last_9_months
        totals = [totals_by_month[month_year] for month_year in month_year_list]

        # Calculate rolling average
        df_totals = pd.Series(totals)
        rolling_avg = df_totals.rolling(window=3, min_periods=1).mean().tolist()

        ax.plot(months, totals, marker="o", label=corp_name, color="b")
        ax.plot(months, rolling_avg, color="r", linestyle="--", label="Rolling Average")
        ax.set_title(f"Monthly Fats for {corp_name}")
        ax.set_xlabel("Months")
        ax.set_ylabel("Total Fats")
        ax.legend()
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        chart = plot_to_base64(fig)
        charts.append({"chart": chart, "title": f"Monthly Fats for {corp_name}"})

    return render(request, "monthly_totals.html", {"charts": charts, "form": form})


def fats_by_type_chart(request):
    if request.method == "POST":
        form = MonthYearForm(request.POST)
        if form.is_valid():
            month = form.cleaned_data["month"]
            year = form.cleaned_data["year"]
    else:
        form = MonthYearForm()
        month = form.fields["month"].initial
        year = form.fields["year"].initial

    fats_by_type = get_fats_by_type_for_members(month, year)

    corp_charts = []
    for corp_name in sorted(fats_by_type.keys()):
        fig, ax = plt.subplots(figsize=(10, 6))  # Rectangular size
        data = fats_by_type[corp_name]
        df = pd.DataFrame(data).T
        df.plot(kind="bar", stacked=True, ax=ax, colormap="viridis")

        ax.set_title(f"Fats by Type for {corp_name}")
        ax.set_xlabel("Characters")
        ax.set_ylabel("Total Fats")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        chart = plot_to_base64(fig)
        corp_charts.append({"chart": chart, "title": f"Fats by Type for {corp_name}"})

    return render(
        request, "fats_by_type.html", {"corp_charts": corp_charts, "form": form}
    )


def upload_csv(request):
    if request.method == "POST" and request.FILES["csv_file"]:
        csv_file = request.FILES["csv_file"]
        fs = FileSystemStorage()
        filename = fs.save(csv_file.name, csv_file)
        uploaded_file_url = fs.url(filename)
        import_csv_to_model(fs.path(filename))
        return render(
            request, "upload_csv.html", {"uploaded_file_url": uploaded_file_url}
        )
    return render(request, "upload_csv.html")
