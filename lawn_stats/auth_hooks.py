"""Hook into Alliance Auth"""

# Django
# Alliance Auth
from django.utils.translation import gettext_lazy as _

from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

# AA Example App
from lawn_stats import urls


class ExampleMenuItem(MenuItemHook):
    """This class ensures only authorized users will see the menu entry"""

    def __init__(self):
        # setup menu entry for sidebar
        MenuItemHook.__init__(
            self,
            _("Base Plugin App"),
            "fas fa-cube fa-fw",
            "lawn_stats:index",
            navactive=["lawn_stats:"],
        )

    def render(self, request):
        """Render the menu item"""

        if request.user.has_perm("lawn_stats.basic_access"):
            return MenuItemHook.render(self, request)

        return ""


@hooks.register("url_hook")
def register_urls():
    """Register app urls"""

    return UrlHook(urls, "lawn_stats", r"^lawn_stats/")
