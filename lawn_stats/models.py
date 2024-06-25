"""
App Models
Create your models in here
"""

from typing import Union

# Django
from django.db import models


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

        return EveonlineEvecorporationinfo.objects.get(pk=self.corporation_id)


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
    def alliance(self) -> Union[EveonlineEveallianceinfo, None]:
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
