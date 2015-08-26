# django elasticmodels


## Indices

indices are created by inheriting from elasticmodels.utils.conf.ESIndex
``` python
from elasticmodels.utils import conf

class MyIndex(conf.ESIndex):
    name = "my-index"  # the `name` of the index in elasticsearch
    settings = {"shards": 5, "replicas": 3}  # the settings for this index

#### in settings.py
ES_INSTALLED_INDICES = [MyIndex(), MyOtherIndex()]
```

## Mappings

the philosophy remains, that a mapping should be in sync, or an aspect of its related django model. all indexable models inherit from elasticmodels.models.SearchableModel.

``` python
from elasticmodels.models import SearchableModel

class MySearchableModel(SearchableModel):
    ... field definitions ...
```

the above is enough to get you up and running, it will create a json document that replicates the models signature as much as possible. if tough, for instance, you are using custom model fields you will need to add a bit more to the definition of the searchable model.

``` python
from myapp.fields import MyCustomField
from elasticmodels.models import SearchableModel

class MySpecialModel(SearchableModel):
    class SearchMeta:
        additional_options = {"foo": {"type": "string","index": "no"}}

    foo = MyCustomField()


# the mapping will now look like this
print(MySpecialModel._search_meta.mapping)
  {"foo": {"type": "string", "index": "no"}, "id": {"type": "long"}}
```

you can even define fields in your mapping that may be aggregates, or properties of fields on your model.

``` python
from django.db import models
from elasticmodels.models import SearchableModel

class Home(SearchableModel):
    class SearchMeta:
        custom_fields = {"location": "geo_point"}
        exclude_fields = ["latitude", "longitude"]

    latitude = models.FloatField()
    longitude = models.FloatField()
    street_address = models.CharField(max_len=100)
```

above we made our Home model with a custom _location_ field that has an elasticsearch type of **geo__point**. but this will not have any auto magical effects besides telling elasticsearch that the mapping definition for this type includes a geopoint. to tell _elasticmodels_ how to deal with this custom field we must write a serializer.

## serializing

all elasticmodels __must__ have a serializer class. by default all subclasses of SearchableModel share the elasticmodels.utils.serializers.ModelJSONSerializer. for most tasks, the prior serializer is enough, but if you have defined custom fields, or prefer a special way of serializing a field you can simply subclass ModelJSONSerializer and tell it how to serialize your field.

``` python
# in myapp/search/serializers.py
from elasticmodels.utils.serializers import ModelJSONSerializer

class HomeSerializer(ModelJSONSerializer):
    def serialize_location(self, instance):
        return {"latitude": instance.latitude, "longitude": instance.longitude}

# in myapp/models.py
from django.db import models
from elasticmodels.models import SearchableModel
from myapp.search import serializers

class Home(SearchableModel):
    class SearchMeta:
        custom_fields = {"location": "geo_point"}
        exclude_fields = ["latitude", "longitude"]
        serializer_class = serializers.HomeSerializer

    latitude = models.FloatField()
    longitude = models.FloatField()
    street_address = models.CharField(max_len=100)
```

when subclassing ModelJSONSerializer to add a custom definition for serializing a field user the following signature as demonstrated above:
  serialize\_**field name**(self, instance) -> serializable type

### implementation

this integration is an implementation of the elasticsearch zero downtime mapping update system. the main purpose for focusing on this sort of (opinionated) implementation is to aid prototyping of your elasticsearch backend along with your django models. say, for instance, you've configured your django model to have an integer field... if you have pushed the mapping of its related document to also have an integer type (or long in elasticsearch)

### why elasticmodels

