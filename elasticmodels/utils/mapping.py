# elasticmodels/utils/mapping_utils.py
# author: andrew young
# email: ayoung@thewulf.org

from __future__ import absolute_import, unicode_literals


FIELD_MAP = {
    "AutoField": "long",
    "BigIntegerField": "long",
    "BinaryField": "binary",
    "BooleanField": "boolean",
    "CharField": "string",
    "CommaSeparatedIntegerField": "short",
    # converts from python datetime.date or datetime.datetime field
    "DateField": "date",
    "DateTimeField": "date",
    "DecimalField": "double",
    # converts from python timedelta type
    "DurationField": "double",
    "EmailField": "string",
    "FloatField": "double",
    "GenericIPAddressField": "string",
    "IPAddressField": "string",
    "IntegerField": "long",
    "PositiveIntegerField": "long",
    "PositiveSmallIntegerField": "short",
    "SmallIntegerField": "short",
    "SlugField": "string",
    "TextField": "string",
    # converts from python datetime.time type
    "TimeField": "string",
    "URLField": "strinng",
    "UUIDField": "string",

    # with the exception of FilePathField, these fields are just the url to the asset
    "ImageField": "string",
    "FileField": "string",
    "FieldFile": "string",
    "FilePathField": "string",

    "ForeignKey": "object",
    "OneToOneField": "object",
    "ManyToManyField": "object"
}

_supported_es_types = set(FIELD_MAP.values())


class SearchField(object):
    """
    """
    def __init__(self, name, db_type, **options):
        self.name = name
        self.db_type = db_type
        self.options = options
        self._mapping = None

    def __repr__(self):
        return "{0}({1}, {2}, {3})".format(self.__class__.__name__, self.name,
            self.db_type, self.es_type)
    __str__ = __repr__

    def get_map(self):
        try:
            es_type = FIELD_MAP[self.db_type.__class__.__name__]
        except (KeyError, AttributeError):
            if self.db_type in _supported_es_types:
                es_type = self.db_type
            else:
                raise NotImplementedError("Mapping for {0} field type has not "
                    "been implemented.".format(self.db_type))
        return es_type

    @property
    def es_type(self):
        es_type = self.get_map()
        return es_type

    @property
    def field_mapping(self):
        if self._mapping is None:
            self._mapping = self._generate_mapping()
        return self._mapping

    def _generate_mapping(self):
        mapping = {"type": self.es_type}
        mapping.update(self.options)
        return mapping

