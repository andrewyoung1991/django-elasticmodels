# manager.py
# author: andrew young
# email: ayoung@thewulf.org

from django.db.models import Manager

from elasticsearch.helpers import bulk as elasticbulk

from elasticmodels.utils import serializers
from elasticmodels.utils.aliasing import AliasedIndex
from elasticmodels.utils.elasticobject import ElasticObject
from elasticmodels.tasks import indexing_task, bulk_indexing_task


class AliasAlreadyExists(Exception): pass


class ElasticModelManager(ElasticObject, Manager):
    """the interface for searching, setting up and managing the elasticsearch
    document related to a django model.
    """
    @indexing_task
    def index_document(self, pk, instance, create=False):
        return self.index(id=pk, body=instance, op_type="create" if create else "index")

    @indexing_task
    def remove_document(self, pk):
        return self.delete(id=pk)

    def search_es(self, raw_only=False, *args, **kwargs):
        """ put a docstring here
        """
        raw_results = self.search(*args, **kwargs)

        if raw_only:
            return raw_results

        results = self._convert_to_queryset(raw_results)
        return results, raw_results

    def _convert_to_queryset(self, raw_results):
        """ takes the raw elasticsearch results and creates a queryset that will
        maintain the ordering of the elasticsearch results.
        """
        pks = [result["_source"]["id"] for result in raw_results["hits"]["hits"]]
        clauses = " ".join(["WHEN id={0} THEN {1}".format(pk, i)
            for i, pk in enumerate(pks)])
        ordering = "CASE {0} END".format(clauses)
        results = self.filter(pk__in=pks)\
            .extra(select={"ordering": ordering}, order_by=("ordering",))
        return results

    def _put_mapping(self):
        return self.indices.put_mapping(index=self.index_name,
            doc_type=self.doctype_name, mapping=self.mapping)

    @bulk_indexing_task
    def index_queryset(self, queryset):
        # TODO
        # elasticbulk
        pass

