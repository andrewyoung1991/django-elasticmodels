# utils/serializer_utils.py
# author: andrew young
# email: ayoung@thewulf.org

import datetime
import decimal
import uuid
import json

from django.db.models import FieldDoesNotExist
from django.db.models.fields.related import ManyToManyField
from django.db.models.query import QuerySet
from django.utils import six, timezone
from django.utils.encoding import force_text
from django.utils.functional import Promise


class JSONEncoder(json.JSONEncoder):
    """
    JSONEncoder subclass that knows how to encode date/time/timedelta,
    decimal types, generators and other basic python objects.
    Taken from https://github.com/tomchristie/django-rest-framework/blob/master/rest_framework/utils/encoders.py
    """
    def default(self, obj):
        # For Date Time string spec, see ECMA 262
        # http://ecma-international.org/ecma-262/5.1/#sec-15.9.1.15
        if isinstance(obj, Promise):
            return force_text(obj)
        elif isinstance(obj, datetime.datetime):
            representation = obj.isoformat()
            if obj.microsecond:
                representation = representation[:23] + representation[26:]
            if representation.endswith('+00:00'):
                representation = representation[:-6] + 'Z'
            return representation
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.time):
            if timezone and timezone.is_aware(obj):
                raise ValueError("JSON can't represent timezone-aware times.")
            representation = obj.isoformat()
            if obj.microsecond:
                representation = representation[:12]
            return representation
        elif isinstance(obj, datetime.timedelta):
            return six.text_type(total_seconds(obj))
        elif isinstance(obj, decimal.Decimal):
            # Serializers will coerce decimals to strings by default.
            return float(obj)
        elif isinstance(obj, uuid.UUID):
            return six.text_type(obj)
        elif isinstance(obj, QuerySet):
            return tuple(obj)
        elif hasattr(obj, 'tolist'):
            # Numpy arrays and array scalars.
            return obj.tolist()
        elif hasattr(obj, '__getitem__'):
            try:
                return dict(obj)
            except:
                pass
        elif hasattr(obj, '__iter__'):
            return tuple(item for item in obj)
        return super(JSONEncoder, self).default(obj)


class ModelJSONSerializer(object):
    """Default elasticsearch serializer for a django model
    usage:
    >>> class MyModel(models.Model):
    ...     my_relation = models.ForeignKey("MyRelation")
    ...
    >>> class MyRelation(models.Model):
    ...     name = models.CharField(max_length=50)
    ...
    >>> class MyModelsSerializer(ModelJSONSerializer):
    ...     # the model to serialize
    ...     # virtual and custom fields take the instance
    ...     def serialize_my_relation(self, instance):
    ...         return {"name": instance.my_relation.name, "id": instance.my_relation.id}
    ...
    >>> my_model_dict = MyModelSerializer(MyModelInstance(my_relation=MyRelation(name="foobar")))
    >>> my_model_dict.serialize(to_json=False)
    ... {"my_relation": {"id": [1, ], "name": "foobar"}}


    when defining methods to serialize custom fields, please use the following signature
        def serialize_<field name>(self, instance): -> (dict || int || str || float)
    """

    def __init__(self, instance):
        self.instance = instance
        self.get_field = instance._meta.get_field
        self.fields = instance._search_meta.fields

    def serialize_field(self, field_name):
        """Takes a field name and returns instance's db value converted
        for elasticsearch indexation.
        """
        method_name = 'serialize_{0}'.format(field_name)
        try:
            return getattr(self, method_name)(self.instance)
        except AttributeError:
            # if this raises an error we can count on the fact this is a
            # custom/virtual field
            field = self.get_field(field_name)

        if field.rel:
            related = getattr(self.instance, field.name).all() if \
                isinstance(field, ManyToManyField) else \
                [getattr(self.instance, field.name), ]
            app_path = related[0].label
            return {"id": [rel.pk for rel in related], "value": app_path}

        return getattr(self.instance, field.name)

    def serialize(self, to_json=True):
        model_dict = dict()
        for field in self.fields:
            try:
                model_dict[field.name] = self.serialize_field(field.name)
            except FieldDoesNotExist:
                raise AttributeError("serialize_{0} method not found".format(field.name))
        return json.dumps(model_dict, cls=JSONEncoder) if to_json else model_dict

