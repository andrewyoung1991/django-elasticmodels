# options.py
# author: andrew young
# email: ayoung@thewulf.org

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist

from elasticsearch import Elasticsearch

from elasticmodels.utils import mapping, serializers, collect_indices


class CustomFieldNotDefinedError(Exception): pass
class IndexNotInstalledError(Exception): pass


class MappingOptions(object):
    """the meta options interface for user to define the structure of
    the elasticsearch document.
    """
    def __init__(self, model, options):
        """options for generating elasticsearch mapping for django model
        """
        self.model = model

        self.index_name = getattr(options, "index_name",
            self.model._meta.app_label.lower())
        self.doctype_name = getattr(options, "doctype_name",
            self.model._meta.object_name.lower())

        # initialize mapping for instance
        self._mapping = {"properties": {}}

        self.id_field = getattr(options, "id_field", "pk")
        self.excluded_fields = getattr(options, "excluded_fields", tuple())
        # mapping of custom fields used in elasticsearch but not in the django db and
        # their related django style fields. See `mapping_utils.FIELD_MAPPING`
        self.custom_fields = getattr(options, "custom_fields", dict())

        # mapping of additional options such as "index" "analyze" "store" etc...
        self.additional_options = getattr(options, "additional_options", dict())

        _fields = getattr(options, "fields", [])
        _fields.extend(self.custom_fields.keys())
        self.fields = self._get_fields(_fields, self.excluded_fields)

        self.id_field_type = getattr(options, "id_field_type", "long")
        self.fields.append(mapping.SearchField("id", self.id_field_type))

        # get the serializer class
        self.serializer_class = getattr(options, "serializer_class",
            serializers.ModelJSONSerializer)

    @property
    def index(self):
        index = collect_indices(self.index_name)
        if isinstance(self.index, (list, tuple)):
            raise IndexNotInstalledError("Please add {0} to ES_INSTALLED_INDICES in"
                " your settings module".format(self.index_name))
        return index

    def _get_fields(self, fields, exclude):
        """
        """
        if not fields:
            _fields = list(field.name for field in self.model._meta.fields if not \
                field.name in exclude)
        else:
            _fields = list(set(fields) - set(exclude))

        fields = []
        for field in _fields:
            # create utils.SearchFields classes here
            try:
                field_class = self.model._meta.get_field(field)
            except FieldDoesNotExist:
                # assuming its a custom field
                try:
                    field_class = self.custom_fields[field]
                except KeyError as err:
                    raise CustomFieldNotDefinedError(err)
            fields.append(
                mapping.SearchField(field, field_class),
                **self.additional_options.get(field, dict()))

        return fields

    @property
    def mapping(self):
        """
        """
        if not self._mapping["properties"]:
            for field in self.fields:
                self._mapping["properties"].update({field.name: field.field_mapping})
        return self._mapping

    def recalculate_mapping(self):
        """
        """
        self._mapping = {"properties": {}}
        return self.mapping

