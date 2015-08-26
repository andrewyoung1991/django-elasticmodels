# utils/__init__.py
# author: andrew young
# email: ayoung@thewulf.org

from django.conf import settings

from elasticmodels.utils.elasticobject import ElasticObject
from elasticmodels.utils.serializers import ModelJSONSerializer
from elasticmodels.utils.conf import ESIndex
from elasticmodels.utils import deepdiff


def diff_dicts(dict_1, dict_2):
    """ returns a boolean indicating if the dicts are different and a DeepDiff
    dict-like object that describes the differences.
    """
    differ = deepdiff.DeepDiff(dict_1, dict_2)
    return len(differ) > 0, differ


def collect_indices(get_index=None):
    installed = getattr(settings, "ES_INSTALLED_INDICES", [])
    assert isinstance(installed, (list, tuple)), \
        "ES_INSTALLED_INDICES must be a list or tuple"
    for index in installed:
        assert isinstance(index, ESIndex), "{0} is not an instance of"\
            " ESIndex".format(index)
        if get_index is not None:
            if index.name == get_index:
                return index
    return installed

