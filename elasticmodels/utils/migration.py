# utils/migration.py
# author: andrew young
# email: ayoung@thewulf.org

import threading

from django.conf import settings

from elasticsearch import helpers

from elasticmodels.utils.elasticobject import ElasticObject


class MigrationError(Exception): pass


class SearchableModelMigrationManager(ElasticObject):
    """ aka the best thing for es and django dev ever
    """
    def __init__(self, alias_name=None):
        self.alias_name = alias_name
        if self.alias_name is None and not hasattr(self, "name"):
            raise AttributeError("No alias name provided.")

    def _get_current_index_name(self):
        """ grabs the name of the currently alaised index
        """
        try:
            alias = self.indices.get_alias(name=self.alias_name)
            return list(alias.keys())[0]
        except:
            return "{alias}_0".format(alias=self.alias_name)

    def get_settings(self):
        return self.indices.\
            get_settings(index=self.alias_name)[self._get_current_index_name()]

    def get_mappings(self):
        return self.indices.\
            get_mapping(index=self.alias_name)[self._get_current_index_name()]

    @property
    def initialized(self):
        """ lets us know if the alias scheme has been initialized
        """
        return self.indices.exists_alias(name=self.alias_name)

    @property
    def models(self):
        from elasticmodels.models import SearchableModel

        models = []
        for model in SearchableModel.__subclasses__():
            if model._search_meta.index_name == self.alias_name:
                if not getattr(model._meta, "abstract", False):
                    models.append(model)

        return models

    def _compose_next_index(self, mappings, settings=None):
        """ setup the next index before migrating data from the previous mapping to the
        new mapping
        """
        initial = not self.initialized
        new_index_name = self._get_current_index_name() if initial else \
            self._get_next_index_name()

        index_body = {"settings": settings, "mappings": mappings}

        self.indices.create(index=new_index_name, body=index_body)
        if initial:
            self.indices.put_alias(index=new_index_name, name=self.alias_name)

        return new_index_name

    def migrate_index(self, role_back=None, elasticsearch=None, settings=None):
        """ when role back is True or an integer, then migrate the documents onto a
        preexisting index version. if role_back is an integer then migrate onto that
        index revision otherwise, if it is True move back one revision.
        """
        self.elasticsearch = self.elasticsearch if elasticsearch is None else elasticsearch
        mappings = {model.es.doctype_name: model._search_meta.mapping for
            model in self.models}

        needs_to_migrate = False # okay
        for doctype, mapping in mappings.items():
            try:
                self.elasticsearch.indices.put_mapping(index=self.alias_name,
                    doc_type=doctype, body=mapping)
            except Exception as e:
                if hasattr(e, "error"):
                    needs_to_migrate = e.error.startswith("MergeMappingException")
                else:
                    raise MigrationError("Exception raised while attempting to "
                        "migrate {0}\n{1}".format(doctype, e))

        if needs_to_migrate is True:
            return self._run_migration(mappings, settings, role_back)
        else:
            return

    def _run_migration(self, mappings, settings, role_back=None):
        if role_back is not None:
            new_name = self._get_next_index_name(previous=role_back)
        else:
            new_name = self._compose_next_index(mappings=mappings, settings=settings)

        old_name = self._get_current_index_name()

        def run():
            # reindex the documents from the old index onto the new index
            helpers.reindex(elasticsearch, old_name, new_name)
            # setup the alias for the new index
            self.indices.put_alias(name=self.alias_name, index=new_name)
            # delete the old alias
            self.indices.delete_alias(name=self.alias_name, index=old_name)
            # delete all the documents in the old index (keep the mapping in case one
            # needs to role back to an older schema
            self.delete_by_query(index=old_name,
                body={"query": {"match_all": {}}})

        thread = threading.Thread(target=run)
        thread.start()

        return thread

    def _get_next_index_name(self, previous=False):
        alias, revision = self._get_current_index_name().rsplit("_", 1)
        if not isinstance(previous, bool):
            revision = previous
        else:
            revision = str(int(revision) + (-1 if previous is True else 1))
        return "{alias}_{revision}".format(alias=alias, revision=revision)

