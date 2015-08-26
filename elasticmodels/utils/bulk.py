# utils/bulk.py
# author: andrew young
# email: ayoung@thewulf.org

from sys import maxsize as maxint
from functools import partial
from collections import deque
import json

from django.db.models import Min, Max

from elasticsearch.helpers import bulk as es_bulk_op

from elasticmodels import connect
from elasticmodels.utils.serializers import JSONEncoder


class ChunkSerializer(object):
    """ a bulk serializer iterator that yields `chunk_size` of elasticsearch action
    dicts.
    see: http://elasticsearch-py.readthedocs.org/en/master/helpers.html#
            elasticsearch.helpers.streaming_bulk
    for more details.
    """
    chunk_size = 100

    def __init__(self, queryset, op_type="update"):
        self.querysets = queryset_chunker(queryset, self.chunk_size)
        self.container = deque(maxlen=self.chunk_size)
        self.op_type = op_type
        self.source_label = "_source" if self.op_type == "index" else "doc"
        self._chunker = None

    def __iter__(self):
        return self.get_chunk()

    def __next__(self):
        if not self._chunker:
            self._chunker = self.get_chunk()
        return next(self._chunker)

    def get_chunk(self):
        for queryset in self.querysets:
            self.container.extend(self._serialize_action(instance) for instance in
                queryset)
            yield self.container
            self.container.clear()

    def _serialize_action(self, instance):
        action = {
            "_op_type": self.op_type,
            "_index": instance.es.index_name,
            "_type": instance.es.doctype_name,
            "_id": instance.pk
        }
        if self.op_type != "delete":
            action.update({self.source_label: instance.es_serialized})
        return action


def queryset_chunker(queryset, chunksize=100):
    ending_pk = queryset.aggregate(Min("pk"))["pk__min"] - 1
    queryset = queryset.order_by("pk")
    while True:
        print(ending_pk)
        out = queryset.filter(pk__gt=ending_pk)[:chunksize]
        yield out.iterator()
        ending_pk = out.aggregate(Max("pk"))["pk__max"]
        if ending_pk is None:
            raise StopIteration


def send_chunks_to_es(chunker, elasticsearch=None, callback=None):
    """ limits the cpu bound task of serializing high quantities of django models
    by serializing small chunks and sending them to elasticsearch
    """
    send_chunk = partial(es_bulk_op,
        elasticsearch or connect(),
        chunk_size=chunker.chunk_size)

    for chunk in chunker:
        result = send_chunk(chunk)
        if callable(callback):
            callback(result)


