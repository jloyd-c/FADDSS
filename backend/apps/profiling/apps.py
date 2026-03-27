from django.apps import AppConfig


class ProfilingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.profiling'
    label = 'profiling'

    def ready(self):
        # Register signal handlers for NormalizedData auto-population.
        # Import here (not at module level) to avoid circular imports
        # and to ensure models are fully loaded before signals connect.
        import apps.profiling.signals  # noqa: F401
