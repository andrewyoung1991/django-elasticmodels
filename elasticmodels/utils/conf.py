# utils/conf.py
# author: andrew young
# email: ayoung@thewulf.org

import functools

from elasticmodels.utils import migration


class ESIndex(migration.SearchableModelMigrationManager):
    name = None
    settings = {}

    def __init__(self, *args, **kwargs):
        assert self.settings is not None, "settings should be a dict"
        super(ESIndex, self).__init__(*args, **kwargs)
        self.migrate_index = functools.partial(self.migrate_index,
            settings=self.settings)
        if self.name:
            self.alias_name = self.name
        if not self.initialized:
            self.initialize()

    def initialize(self):
        mappings = {m.es.doctype_name: m._search_meta.mapping for m in self.models}
        self._compose_next_index(mappings, self.settings)
        assert self.indices.exists_alias(self.alias_name), "Something went wrong, "\
            "the index could not be initialized"

    def update_settings(self, **kwargs):
        return self.indices.put_settings(index=self.name, body=self.settings, **kwargs)

