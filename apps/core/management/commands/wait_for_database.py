import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    help = "Wait for PostgreSQL, optionally until all migrations have applied."

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=float, default=60)
        parser.add_argument("--migrations", action="store_true")

    def handle(self, *args, **options):
        deadline = time.monotonic() + options["timeout"]
        while time.monotonic() < deadline:
            try:
                connection.ensure_connection()
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                if options["migrations"]:
                    executor = MigrationExecutor(connection)
                    if executor.migration_plan(executor.loader.graph.leaf_nodes()):
                        time.sleep(1)
                        continue
                self.stdout.write("Database is ready")
                return
            except Exception:
                connection.close()
                time.sleep(1)
        raise CommandError("Database or migrations were not ready before timeout")
