# models.py
# author: andrew young
# email: ayoung@thewulf.org

from __future__ import unicode_literals, absolute_import

import uuid
from functools import partial

from django.conf import settings
from django.db import models
from django.db.models import signals
from django.db.models.base import ModelBase, Model
from django.utils import six

from elasticsearch import Elasticsearch

from elasticmodels.options import MappingOptions
from elasticmodels.utils.elasticobject import ElasticDoctype
from elasticmodels.manager import ElasticModelManager
from elasticmodels.utils.fields import JSONField


class SearchableModelMeta(ModelBase):
    """ metaclass for searchable models. essentially the same as the django
    model base, with the exception of the creation of the `_search_meta` attribute
    which stores options / info about the initialization of the index.
    """
    def __new__(cls, name, bases, options):
        search_options = options.get("MappingMeta")

        the_class = super(SearchableModelMeta, cls).__new__(cls, name, bases, options)
        # drop the search options in
        search_options = MappingOptions(the_class, search_options)
        the_class.add_to_class("_search_meta", search_options)

        # we really want the object manager to be a subclass of ElasticModelManager
        if not getattr(the_class._meta, "abstract"):
            # we can assume this attribute exists as a result of the super() call earlier
            if issubclass(the_class.objects.__class__, ElasticModelManager):
                # give the manager our index properties
                setattr(the_class.objects, "index_name", search_options.index_name)
                setattr(the_class.objects, "doctype_name", search_options.doctype_name)
                setattr(the_class.objects, "mapping", search_options.mapping)
            else:
                raise TypeError("{model} `objects` attribute must be a subclass of"
                    " ElasticModelManager".format(model=the_class))

        return the_class


class SearchableModel(six.with_metaclass(SearchableModelMeta, Model)):
    """
    .. py:class:: SearchableModel
        the abstract base class / mixin for a django model that will be
        indexed in elasticsearch.

        .. py:class:: SearchMeta
            .. py:attribute:: excluded_fields
            .. py:attribute:: custom_fields
            .. py:attribute:: additional_options
            .. py:attribute:: fields
            .. py:attribute:: index_name
            .. py:attribute:: doctype_name
            .. py:attribute:: serializer_class

        .. py:classmethod:: send_queryset_to_elasticsearch(always_index=True, **filters)
            bulk indexes/updates a queryset in elasticsearch
            :param always_index: if true, updates all members of the querysets
                is_elasticsearch_indexable paramter to True
            :param \**filters: key value pairs to pass to Queryset.filter()
            :rtype: a queryset

        .. py:classmethod:: remove_queryset_from_elasticsearch(never_index=True,
                **filters)
            bulk deletes a queryset from elasticsearch
            :param always_index: if true, updates all members of the querysets
                is_elasticsearch_indexable paramter to False
            :param \**filters: key value pairs to pass to Queryset.filter()
            :rtype: a queryset

        .. py:method:: remove_from_elasticsearch(never_index=True)
            removes instances related document from elasticsearch
            :param never_index: if true, mark instances is_elasticsearch_indexable=False
            :type never_index: bool
            :rtype: self

        .. py:method:: send_to_elasticsearch(always_index=True)
            indexes/updates related document in elasticsearch
            :param always_index: if true, mark instances is_elasticsearch_indexable=True
            :type always_index: bool
            :rtype: self
    """
    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super(SearchableModel, self).__init__(*args, **kwargs)
        self.es_index_name = self._search_meta.index_name
        self.es_doctype_name = self._search_meta.doctype_name
        self.es = None

    is_elasticsearch_indexable = models.BooleanField(default=True)
    date_last_updated = models.DateTimeField(auto_now=True)
    objects = ElasticModelManager()

    def send_to_elasticsearch(self, always_index=False):
        if self.is_elasticsearch_indexable or always_index:
            if always_index:
                self.is_elasticsearch_indexable = True
                self.save()  # saving will automatically add to es
            else:
                self.es.update_document(self.es_serialized)
        return self

    def remove_from_elasticsearch(self, never_index=False):
        self.es.remove_document()
        if never_index:
            self.is_elasticsearch_indexable = False
            self.save()
        return self

    @property
    def es_serialized(self):
        serializer = self._search_meta.serializer_class(self)
        return serializer.serialize(to_json=True)


def update_es_instance(sender, instance, **kwargs):
    """ post save reciever for SearchableModel subclasses
    simply initializes the model .es object, serializes it, and ships the document for
    indexing in elasticsearch.
    """
    if issubclass(sender, SearchableModel):
        created = kwargs.get("created", False)
        if created:
            instance.es = ElasticDoctype(instance.es_index_name,
                    instance.es_doctype_name, instance.pk)
            instance.es.update_document(instance.es_serialized)
        else:
            instance.send_to_elasticsearch()


def remove_es_instance(sender, instance, **kwargs):
    """ post delete reciever for SearchableModel subclasses.
    """
    if issubclass(sender, SearchableModel):
        instance.remove_from_elasticsearch()


if getattr(settings, "ES_AUTO_SYNC", True):
    signals.post_save.connect(update_es_instance, dispatch_uid=uuid.uuid1())
    signals.pre_delete.connect(remove_es_instance, dispatch_uid=uuid.uuid1())


from elasticmodels.utils.migration import SearchableModelMigrationManager as \
    MigrationManager

