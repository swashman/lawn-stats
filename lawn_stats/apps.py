"""App Configuration"""

# Django
# AA example App
from django.apps import AppConfig

from lawn_stats import __version__


class ExampleConfig(AppConfig):
    """App Config"""

    name = "lawn_stats"
    label = "lawn_stats"
    verbose_name = f"lawn_stats App v{__version__}"
