import base64
import io
import urllib

import matplotlib.pyplot as plt
import pandas as pd

from django.core.files.storage import FileSystemStorage
from django.db.models import Avg
from django.shortcuts import render

from .data_processing import (
    get_fats_by_type_for_members,
    get_monthly_totals_by_corporation,
    get_total_fats_by_corporation,
    import_csv_to_model,
)
from .forms import MonthYearForm


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
    fig, ax = plt.subplots(figsize=(10, 6))  # Rectangular size
    corporations = [corp["character__corporation_name"] for corp in corp_totals]
    totals = [corp["total_fats"] for corp in corp_totals]
    ax.bar(corporations, totals, color=plt.cm.viridis(range(len(corporations))))
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
    total_mains = 3  # Example value; adjust as needed
    relative_participation = {
        corp["character__corporation_name"]: corp["total_fats"] / total_mains
        for corp in corp_totals
    }

    fig, ax = plt.subplots(figsize=(10, 6))  # Rectangular size
    corporations = list(relative_participation.keys())
    participation = list(relative_participation.values())
    ax.bar(corporations, participation, color=plt.cm.viridis(range(len(corporations))))
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

    fig, ax = plt.subplots(figsize=(10, 6))  # Rectangular size
    for corp_name in corp_names:
        corp_data = monthly_totals.filter(character__corporation_name=corp_name)
        months = [f"{total['year']}-{total['month']:02d}" for total in corp_data]
        totals = [total["total_fats"] for total in corp_data]
        ax.plot(months, totals, marker="o", label=corp_name)

    avg_total = monthly_totals.aggregate(Avg("total_fats"))["total_fats__avg"]
    ax.axhline(y=avg_total, color="r", linestyle="--", label="Average")
    ax.set_title("Monthly Fats for Corporations")
    ax.set_xlabel("Months")
    ax.set_ylabel("Total Fats")
    ax.legend()
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    chart = plot_to_base64(fig)
    return render(
        request,
        "chart.html",
        {"chart": chart, "title": "Monthly Fats for Corporations", "form": form},
    )


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
    corp_names = fats_by_type.values_list(
        "character__corporation_name", flat=True
    ).distinct()
    link_types = fats_by_type.values_list(
        "fatlink__link_type__name", flat=True
    ).distinct()

    fig, ax = plt.subplots(figsize=(10, 6))  # Rectangular size
    data = {
        corp_name: {link_type: 0 for link_type in link_types}
        for corp_name in corp_names
    }

    for fat in fats_by_type:
        corp_name = fat["character__corporation_name"]
        link_type = fat["fatlink__link_type__name"]
        data[corp_name][link_type] += fat["total_fats"]

    df = pd.DataFrame(data).T
    df.plot(kind="bar", stacked=True, ax=ax, colormap="viridis")

    ax.set_title("Fats by Type for Corporations")
    ax.set_xlabel("Corporations")
    ax.set_ylabel("Total Fats")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    chart = plot_to_base64(fig)
    return render(
        request,
        "chart.html",
        {"chart": chart, "title": "Fats by Type for Corporations", "form": form},
    )


def individual_fats_by_type_chart(request):
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
    corp_names = fats_by_type.values_list(
        "character__corporation_name", flat=True
    ).distinct()

    charts = []
    for corp_name in corp_names:
        fig, ax = plt.subplots(figsize=(10, 6))  # Rectangular size
        corp_fats = fats_by_type.filter(character__corporation_name=corp_name)
        data = {
            fat["character__character_name"]: {
                link_type: 0
                for link_type in corp_fats.values_list(
                    "fatlink__link_type__name", flat=True
                ).distinct()
            }
            for fat in corp_fats
        }

        for fat in corp_fats:
            character_name = fat["character__character_name"]
            link_type = fat["fatlink__link_type__name"]
            data[character_name][link_type] += fat["total_fats"]

        df = pd.DataFrame(data).T
        df.plot(kind="bar", stacked=True, ax=ax, colormap="viridis")

        ax.set_title(f"Fats by Type for {corp_name}")
        ax.set_xlabel("Characters")
        ax.set_ylabel("Total Fats")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        chart = plot_to_base64(fig)
        charts.append({"chart": chart, "title": f"Fats by Type for {corp_name}"})

    return render(
        request, "individual_fats_by_type.html", {"charts": charts, "form": form}
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
