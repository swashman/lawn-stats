"""
App Models
Create your models in here
"""

from django.core.exceptions import ObjectDoesNotExist

# Django
from django.db import models

from allianceauth.services.hooks import ServicesHook, get_extension_logger

logger = get_extension_logger(__name__)
SERVICE_DB = {
    "mumble": "mumble",
    "smf": "smf",
    "discord": "discord",
    "discorse": "discourse",
    "Wiki JS": "wikijs",
    "ips4": "ips4",
    "openfire": "openfire",
    "phpbb3": "phpbb3",
    "teamspeak3": "teamspeak3",
}


class General(models.Model):
    """Meta model for app permissions"""

    class Meta:
        """Meta definitions"""

        managed = False
        default_permissions = ()
        permissions = (("basic_access", "Can access this app"),)


class MonthlyFleetType(models.Model):
    name = models.CharField(max_length=100)
    source = models.CharField(max_length=10)  # 'Imp' or 'afat'
    month = models.IntegerField()
    year = models.IntegerField()

    class Meta:
        unique_together = ("name", "source", "month", "year")


class MonthlyCorpStats(models.Model):
    corporation_id = models.PositiveIntegerField()
    month = models.IntegerField()
    year = models.IntegerField()
    fleet_type = models.ForeignKey(MonthlyFleetType, on_delete=models.CASCADE)
    total_fats = models.PositiveIntegerField()

    class Meta:
        unique_together = ("corporation_id", "month", "year", "fleet_type")

    def get_corporation(self):

        return EveonlineEvecorporationinfo.objects.get(
            corporation_id=self.corporation_id
        )


class MonthlyUserStats(models.Model):
    user_id = models.PositiveIntegerField()
    corporation_id = models.PositiveIntegerField()
    month = models.IntegerField()
    year = models.IntegerField()
    fleet_type = models.ForeignKey(MonthlyFleetType, on_delete=models.CASCADE)
    total_fats = models.PositiveIntegerField()

    class Meta:
        unique_together = ("user_id", "month", "year", "fleet_type")

    def get_user(self):

        return AuthUser.objects.get(pk=self.user_id)

    def get_corporation(self):

        return EveonlineEvecorporationinfo.objects.get(pk=self.corporation_id)


class FleetTypeLimit(models.Model):
    name = models.CharField(max_length=100)
    limit = models.IntegerField()

    def __str__(self):
        return f"{self.name}: {self.limit}"


class CSVColumnMapping(models.Model):
    column_name = models.CharField(max_length=100, unique=True)
    mapped_to = models.CharField(max_length=100, blank=True, null=True)


class IgnoredCSVColumns(models.Model):
    column_name = models.CharField(max_length=100)

    def __str__(self):
        return self.column_name


class MonthlyCreatorStats(models.Model):
    creator_id = models.IntegerField()
    month = models.IntegerField()
    year = models.IntegerField()
    fleet_type = models.ForeignKey(MonthlyFleetType, on_delete=models.CASCADE)
    total_created = models.IntegerField(default=0)

    class Meta:
        unique_together = (("creator_id", "month", "year", "fleet_type"),)

    def get_creator(self):

        return AuthUser.objects.get(pk=self.creator_id)


class UnknownAccount(models.Model):
    account_name = models.CharField(max_length=255, unique=True)
    user_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.account_name


# LAWN SECONDARY MODELS
################################################################


class AfatDuration(models.Model):
    duration = models.PositiveIntegerField()
    fleet = models.ForeignKey("AfatFatlink", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "afat_duration"
        app_label = "secondary_app"


class AfatFat(models.Model):
    system = models.CharField(max_length=100, blank=True, null=True)
    shiptype = models.CharField(max_length=100, blank=True, null=True)
    character = models.ForeignKey(
        "EveonlineEvecharacter", models.DO_NOTHING, related_name="afat_fats"
    )
    fatlink = models.ForeignKey(
        "AfatFatlink", models.DO_NOTHING, related_name="afat_fats"
    )

    class Meta:
        managed = False
        db_table = "afat_fat"
        unique_together = (("character", "fatlink"),)
        app_label = "secondary_app"


class AfatFatlink(models.Model):
    created = models.DateTimeField()
    fleet = models.CharField(max_length=254)
    hash = models.CharField(unique=True, max_length=254)
    creator = models.ForeignKey(
        "AuthUser",
        models.DO_NOTHING,
        related_name="+",
    )
    link_type = models.ForeignKey(
        "AfatFleettype",
        models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="+",
    )
    is_esilink = models.IntegerField()
    esi_fleet_id = models.BigIntegerField(blank=True, null=True)
    is_registered_on_esi = models.IntegerField()
    character = models.ForeignKey(
        "EveonlineEvecharacter",
        models.DO_NOTHING,
        blank=True,
        null=True,
        related_name="+",
    )
    reopened = models.IntegerField()
    esi_error_count = models.IntegerField()
    last_esi_error = models.CharField(max_length=15)
    last_esi_error_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "afat_fatlink"
        app_label = "secondary_app"


class AfatFleettype(models.Model):
    name = models.CharField(max_length=254)
    is_enabled = models.IntegerField()

    class Meta:
        managed = False
        db_table = "afat_fleettype"
        app_label = "secondary_app"


class AfatLog(models.Model):
    log_time = models.DateTimeField()
    log_event = models.CharField(max_length=11)
    log_text = models.TextField()
    fatlink_hash = models.CharField(max_length=254)
    user = models.ForeignKey("AuthUser", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "afat_log"
        app_label = "secondary_app"


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "auth_user"
        app_label = "secondary_app"


class AuthenticationCharacterownership(models.Model):
    owner_hash = models.CharField(unique=True, max_length=28)
    character = models.OneToOneField(
        "EveonlineEvecharacter", models.DO_NOTHING, related_name="character_ownership"
    )
    user = models.ForeignKey(
        AuthUser, models.DO_NOTHING, related_name="character_ownerships"
    )

    class Meta:
        managed = False
        db_table = "authentication_characterownership"
        app_label = "secondary_app"


class AuthenticationState(models.Model):
    name = models.CharField(unique=True, max_length=32)
    priority = models.IntegerField(unique=True)
    public = models.IntegerField()

    class Meta:
        managed = False
        db_table = "authentication_state"
        app_label = "secondary_app"


class AuthenticationUserprofile(models.Model):
    main_character = models.OneToOneField(
        "EveonlineEvecharacter", models.DO_NOTHING, blank=True, null=True
    )
    state = models.ForeignKey(AuthenticationState, models.DO_NOTHING)
    user = models.OneToOneField(AuthUser, models.DO_NOTHING, related_name="profile")
    language = models.CharField(max_length=10)
    night_mode = models.IntegerField(blank=True, null=True)
    theme = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "authentication_userprofile"
        app_label = "secondary_app"


class EveonlineEveallianceinfo(models.Model):
    alliance_id = models.PositiveIntegerField(unique=True)
    alliance_name = models.CharField(max_length=254)
    alliance_ticker = models.CharField(max_length=254)
    executor_corp_id = models.PositiveIntegerField()

    class Meta:
        managed = False
        db_table = "eveonline_eveallianceinfo"
        app_label = "secondary_app"


class EveonlineEvecorporationinfo(models.Model):
    corporation_id = models.PositiveIntegerField(unique=True)
    corporation_name = models.CharField(max_length=254)
    corporation_ticker = models.CharField(max_length=254)
    member_count = models.IntegerField()
    alliance = models.ForeignKey(
        EveonlineEveallianceinfo, models.DO_NOTHING, blank=True, null=True
    )
    ceo_id = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "eveonline_evecorporationinfo"
        app_label = "secondary_app"


class EveonlineEvecharacter(models.Model):
    character_id = models.PositiveIntegerField(unique=True)
    character_name = models.CharField(max_length=254)
    corporation_id = models.PositiveIntegerField()
    corporation_name = models.CharField(max_length=254)
    corporation_ticker = models.CharField(max_length=5)
    alliance_id = models.PositiveIntegerField(blank=True, null=True)
    alliance_name = models.CharField(max_length=254, blank=True, null=True)
    alliance_ticker = models.CharField(max_length=5, blank=True, null=True)
    faction_id = models.PositiveIntegerField(blank=True, null=True)
    faction_name = models.CharField(max_length=254, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "eveonline_evecharacter"
        app_label = "secondary_app"

    @property
    def alliance(self) -> EveonlineEveallianceinfo | None:
        """
        Pseudo foreign key from alliance_id to EveAllianceInfo
        :raises: EveAllianceInfo.DoesNotExist
        :return: EveAllianceInfo or None
        """
        if self.alliance_id is None:
            return None
        return EveonlineEveallianceinfo.objects.get(alliance_id=self.alliance_id)

    @property
    def corporation(self) -> EveonlineEvecorporationinfo:
        """
        Pseudo foreign key from corporation_id to EveCorporationInfo
        :raises: EveCorporationInfo.DoesNotExist
        :return: EveCorporationInfo
        """
        return EveonlineEvecorporationinfo.objects.get(
            corporation_id=self.corporation_id
        )


class CorpstatsCorpstat(models.Model):
    last_update = models.DateTimeField()
    corp = models.OneToOneField("EveonlineEvecorporationinfo", models.DO_NOTHING)
    token = models.ForeignKey("EsiToken", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "corpstats_corpstat"
        app_label = "secondary_app"

    def get_stats(self):
        """
        return all corpstats for corp

        :return:
        Mains with Alts Dict
        Members List[EveCharacter]
        Un-registered QuerySet[CorpMember]
        """

        linked_chars = EveonlineEvecharacter.objects.filter(
            corporation_id=self.corp.corporation_id
        )  # get all authenticated characters in corp from auth internals
        linked_chars = linked_chars | EveonlineEvecharacter.objects.filter(
            character_ownership__user__profile__main_character__corporation_id=self.corp.corporation_id
        )  # add all alts for characters in corp

        services = [svc.name for svc in ServicesHook.get_services()]  # services list

        linked_chars = linked_chars.select_related(
            "character_ownership", "character_ownership__user__profile__main_character"
        ).prefetch_related("character_ownership__user__character_ownerships")
        skiped_services = []
        for service in services:
            if service in SERVICE_DB:
                linked_chars = linked_chars.select_related(
                    f"character_ownership__user__{SERVICE_DB[service]}"
                )
            else:
                skiped_services.append(service)
                logger.error(f"Unknown Service {service} Skipping")

        for service in skiped_services:
            services.remove(service)

        linked_chars = linked_chars.order_by("character_name")  # order by name

        members = []  # member list
        orphans = []  # orphan list
        alt_count = 0  #
        services_count = {}  # for the stats
        for service in services:
            services_count[service] = 0  # prefill

        mains = {}  # main list
        temp_ids = []  # filter out linked vs unreg'd
        for char in linked_chars:
            try:
                main = (
                    char.character_ownership.user.profile.main_character
                )  # main from profile
                if main is not None:
                    if (
                        main.corporation_id == self.corp.corporation_id
                    ):  # iis this char in corp
                        if main.character_id not in mains:  # add array
                            mains[main.character_id] = {
                                "main": main,
                                "alts": [],
                                "services": {},
                            }
                            for service in services:
                                mains[main.character_id]["services"][
                                    service
                                ] = False  # pre fill

                        if char.character_id == main.character_id:
                            for service in services:
                                try:
                                    if hasattr(
                                        char.character_ownership.user,
                                        SERVICE_DB[service],
                                    ):
                                        mains[main.character_id]["services"][
                                            service
                                        ] = True
                                        services_count[service] += 1
                                except Exception as e:
                                    logger.error(e)

                        mains[main.character_id]["alts"].append(
                            char
                        )  # add to alt listing

                    if char.corporation_id == self.corp.corporation_id:
                        members.append(char)  # add to member listing as a known char
                        if not char.character_id == main.character_id:
                            alt_count += 1
                        if main.corporation_id != self.corp.corporation_id:
                            orphans.append(char)

                    temp_ids.append(char.character_id)  # exclude from un-authed

            except ObjectDoesNotExist:  # main not found we are unauthed
                pass

        unregistered = CorpstatsCorpmember.objects.filter(corpstats=self).exclude(
            character_id__in=temp_ids
        )  # filter corpstat list for unknowns
        tracking = CorpstatsCorpmember.objects.filter(corpstats=self).filter(
            character_id__in=temp_ids
        )  # filter corpstat list for unknowns

        # yay maths
        total_mains = len(mains)
        total_unreg = len(unregistered)
        total_members = len(members) + total_unreg  # is unreg + known
        # yay more math
        auth_percent = len(members) / total_members * 100
        alt_ratio = 0

        try:
            alt_ratio = total_mains / alt_count
        except:
            pass
        # services
        service_percent = {}
        for service in services:
            if service in SERVICE_DB:
                try:
                    service_percent[service] = {
                        "cnt": services_count[service],
                        "percent": services_count[service] / total_mains * 100,
                    }
                except Exception:
                    service_percent[service] = {
                        "cnt": services_count[service],
                        "percent": 0,
                    }

        return (
            members,
            mains,
            orphans,
            unregistered,
            total_mains,
            total_unreg,
            total_members,
            auth_percent,
            alt_ratio,
            service_percent,
            tracking,
            services,
        )


class CorpstatsCorpmember(models.Model):
    character_id = models.PositiveIntegerField()
    character_name = models.CharField(max_length=50)
    location_id = models.BigIntegerField(blank=True, null=True)
    location_name = models.CharField(max_length=150, blank=True, null=True)
    ship_type_id = models.PositiveIntegerField(blank=True, null=True)
    ship_type_name = models.CharField(max_length=42, blank=True, null=True)
    start_date = models.DateTimeField(blank=True, null=True)
    logon_date = models.DateTimeField(blank=True, null=True)
    logoff_date = models.DateTimeField(blank=True, null=True)
    base_id = models.PositiveIntegerField(blank=True, null=True)
    corpstats = models.ForeignKey("CorpstatsCorpstat", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "corpstats_corpmember"
        unique_together = (("corpstats", "character_id"),)
        app_label = "secondary_app"


class CorputilsCorpstats(models.Model):
    last_update = models.DateTimeField()
    corp = models.OneToOneField("EveonlineEvecorporationinfo", models.DO_NOTHING)
    token = models.ForeignKey("EsiToken", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "corputils_corpstats"
        app_label = "secondary_app"

    @property
    def main_count(self):
        return len(self.mains)

    @property
    def mains(self):
        return self.members.filter(
            pk__in=[
                m.pk
                for m in self.members.all()
                if m.main_character
                and int(m.main_character.character_id) == int(m.character_id)
            ]
        )


class CorputilsCorpmember(models.Model):
    character_id = models.PositiveIntegerField()
    character_name = models.CharField(max_length=37)
    corpstats = models.ForeignKey(
        "CorputilsCorpstats", models.DO_NOTHING, related_name="members"
    )

    class Meta:
        managed = False
        db_table = "corputils_corpmember"
        unique_together = (("corpstats", "character_id"),)
        app_label = "secondary_app"

    @property
    def character(self):
        try:
            return EveonlineEvecharacter.objects.get(character_id=self.character_id)
        except EveonlineEvecharacter.DoesNotExist:
            return None

    @property
    def main_character(self):
        try:
            return self.character.character_ownership.user.profile.main_character
        except (
            AuthenticationCharacterownership.DoesNotExist,
            AuthenticationUserprofile.DoesNotExist,
            AttributeError,
        ):
            return None


class EsiToken(models.Model):
    created = models.DateTimeField()
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    character_id = models.IntegerField()
    character_name = models.CharField(max_length=100)
    token_type = models.CharField(max_length=100)
    character_owner_hash = models.CharField(max_length=254)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING, blank=True, null=True)
    sso_version = models.IntegerField()

    class Meta:
        managed = False
        db_table = "esi_token"
        app_label = "secondary_app"
