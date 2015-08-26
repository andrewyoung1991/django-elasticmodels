# utils/elasticobject.py
# author: andrew young
# email: ayoung@thewulf.org

from functools import partial

from django.conf import settings

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError


class ElasticObject(object):
    """a simple object that has a gettable/settable elasticsearch attribute
    the __getattr__ magic method also acts as a proxy to the elasticsearch object.
    """
    _elastic = None
    _chunk_size = getattr(settings, "ELASTIC_CHUNK_SIZE", 500)

    @property
    def indices(self):
        """a proxy for the indices client
        """
        return self.elasticsearch.indices

    def __getattr__(self, key):
        """proxy Elasticsearch class as much as possible
        """
        object_ = self.elasticsearch.__getattribute__(key)
        if callable(object_):
            object_ = partial(object_, index=self.index_name,
                doc_type=self.doctype_name)
        return object_

    def _get_es(self):
        from elasticmodels import connect
        if not self._elastic:
            self._elastic = connect()
        return self._elastic

    def _set_es(self, es_obj):
        assert isinstance(es_obj, Elasticsearch)
        self._elastic = es_obj
        return self.elasticsearch

    elasticsearch = property(_get_es, _set_es)


class ElasticDoctype(ElasticObject):
    def __init__(self, index_name, doctype_name, pk):
        self.index_name = index_name
        self.doctype_name = doctype_name
        self.pk = pk
        for field in [index_name, doctype_name, pk]:
            assert field is not None

    def __getattr__(self, key):
        """proxy Elasticsearch class as much as possible
        """
        object_ = self.elasticsearch.__getattribute__(key)
        if callable(object_):
            object_ = partial(object_, index=self.index_name,
                doc_type=self.doctype_name)
        return object_

    def get_document(self, **kwargs):
        return self.get(id=self.pk, **kwargs)

    def update_document(self, body, **kwargs):
        return self.index(id=self.pk, body=body, **kwargs)

    def create_document(self, body, **kwargs):
        return self.create(id=self.pk, body=body, **kwargs)

    def remove_document(self, **kwargs):
        try:
            self.delete(id=self.pk, **kwargs)
        except NotFoundError:
            pass

    def document_exists(self):
        return self.exists(id=self.pk)

    def explain_query(self, body, **kwargs):
        return self.explain(id=self.pk, body=body, **kwargs)

