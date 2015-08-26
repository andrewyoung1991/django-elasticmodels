# utils/aliasing.py
# author: andrew young
# email: ayoung@thewulf.org

from django.conf import settings

from elasticsearch.helpers import reindex

from .elasticobject import ElasticObject


class AliasedIndex(ElasticObject):
    """
    """
    def __init__(self, alias_name, alias_options=None):
        self.alias_name = alias_name
        self.alias_options = alias_options

    @property
    def alias_exists(self):
        # perhaps the alias has been setup, but it is not pointing to this index yet
        return self.elasticsearch.indices.exists_alias(self.alias_name)

    @property
    def current_revision_number(self):
        revision_number = 0
        if self.alias_exists:
            index_name = "{alias}_*".format(alias=self.alias_name)
            current = self.elasticsearch.indices.get_alias(index=index_name, name=self.alias_name).keys()[0]
            revision_number = int(current.rsplit("_", 1)[-1])
        return revision_number

    def get_index_name(self, revision_number=0):
        return "{alias}_{revision}".format(alias=self.alias, revision=str(revision_number))

    def _setup_alias(self, mappings=None, settings=None):
        """since we only want a single index to be aliased at a time,
        this method will check for the alias and delete the current alias if
        it is different from the index_name.
        """
        index = self.get_index_name()
        self.elasticsearch.indices.create(
            index="", body={"settings": settings, "mappings": mappings})

        if self.alias_exists:
            existing_index = self.index_name(self.current_revision_number)
            new_index = self.index_name(self.current_revision_number + 1)
            # reindex from the existing aliased index onto the new index
            reindex(self.elasticsearch, existing_index, new_index,
                chunk_size=self._chunk_size)
            self.elasticsearch.indices.delete_alias(index=existing_index,
                name=self.alias_name)

        self.elasticsearch.indices.put_alias(
            index=self.index_name, name=self.alias_name)

    def increment_index(self, mappings, settings=None):
        pass

    def decrement_index(self):
        pass

    def migrate(self, forward=True, mappings=None, settings=None):
        if not self.alias_exists:
            self.setup_alias(mappings, settings)
        elif forward:
            self.increment_index(mappings, settings)
        else:
            self.decrement_index()

