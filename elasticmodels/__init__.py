# elasticmodels/__init__.py
# author: andrew young
# email: ayoung@thewulf.org

import warnings

from django.conf import settings

from elasticsearch import Elasticsearch


es_hosts = getattr(settings, "ES_HOSTS", ["localhost:9200"])


def connect(hosts=None, **kwargs):
    assert isinstance(hosts, (list, tuple, type(None))), \
        "`hosts` attribute must be list or tuple."
    if not hosts:
        hosts = es_hosts
    return Elasticsearch(hosts, **kwargs)


def check_connection(elasticsearch=None):
    """ if check connection returns True then the host is valid and elasticsearch is
    ready to party.
    """
    if elasticsearch is None:
        elasticsearch = connect()
    return elasticsearch.ping()

