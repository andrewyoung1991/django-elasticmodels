# managment/commands/migrate_index.py
# author: andrew young
# email: ayoung@thewulf.org

from django.core.management.base import BaseCommand

from elasticmodels.utils import collect_indices
from elasticmodels.exceptions import IndexNotInstalledError


class Command(BaseCommand):
    """ here we will handle the clients request to migrate an index
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "index_name",
            help="")
        parser.add_argument(
            "--role-back",
            dest="role_back",
            default=False,
            action="store_true",
            help="role back a single migration.")
        parser.add_argument(
            "--migration-number",
            dest="migration_number",
            default=None,
            type=int,
            help="role back to a specific migration number.")

    def handle(self, *args, **options):
        alias = options["index_name"]
        role_back = options["role_back"]
        migration_number = options["migration_number"]
        index = collect_indices(alias)

        if isinstance(index, (list, tuple)):
            raise IndexNotInstalledError(
                self.style.ERROR("{0} not installed.".format(index)))

        migration = migration_number if migration_number is not None else role_back
        index.migrate_index(role_back=migration, settings=index.settings,
            verbose=self.style)

