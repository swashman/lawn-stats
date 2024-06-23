# myapp/db_router.py


class SecondaryDBRouter:
    """
    A router to control all database operations on models in the secondary database.
    """

    def db_for_read(self, model, **hints):
        """
        Directs read operations for certain models to the secondary database.
        """
        if model._meta.app_label == "secondary_app":
            return "secondary"
        return "default"

    def db_for_write(self, model, **hints):
        """
        Prevents write operations for models in the secondary database.
        """
        if model._meta.app_label == "secondary_app":
            return None  # Prevent writes to the secondary database
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the secondary_app is involved.
        """
        if (
            obj1._meta.app_label == "secondary_app"
            or obj2._meta.app_label == "secondary_app"
        ):
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the secondary_app models do not get migrated in the secondary database.
        """
        if db == "secondary":
            return False  # Prevent migrations on the secondary database
        return True
