"""
2015 08 26 -- can't get skipUnless to work when @modify_settings is used
"""
# tests/test_elasticmodel.py
# author: andrew young
# email: ayoung@thewulf.org

from django import test
from django.utils.unittest import skipUnless
from django.db import models as dmod

from elasticmodels.models import SearchableModel
from elasticmodels.utils.conf import ESIndex
from elasticmodels.options import MappingOptions
from elasticmodels import check_connection, connect
from elasticmodels.utils.serializers import ModelJSONSerializer


class MockModel(SearchableModel):

    class Meta:
        abstract = True

    class MappingMeta:
        index_name = "a-cool-index"
        fields = ["test_int", "test_char", "test_float"]

    test_int = dmod.SmallIntegerField()
    test_char = dmod.CharField(max_length=10)
    test_float = dmod.FloatField()


class TestModelA(MockModel):
    class MappingMeta:
        index_name = "a-cool-index"


class TestModelBSerializer(ModelJSONSerializer):
    def serialize_tricky_field(self, instance):
        return {"tricky_field": {"foo": "bar"}, "test": instance.test_int}


class TestModelB(MockModel):
    class MappingMeta:
        fields = ["test_int"]
        custom_fields = {"tricky_field": "object"}
        serializer_class = TestModelBSerializer


class ACoolIndex(ESIndex):
    name = "a-cool-index"


@skipUnless(check_connection(), "invalid connection to elasticsearch.")
class ESTestSuite(test.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass


@skipUnless(check_connection(), "invalid connection to elasticsearch.")
class TestModels(ESTestSuite):
    # tests
    def setUp(self):
        self.instance_default = TestModelA(
            test_char="hello, world", test_int=24,
            test_float=3.1415927)
        self.instance_default_2 = TestModelB(
            test_char="hello, world", test_int=24,
            test_float=3.1415927)

    def test_default_mapping_is_dictionary(self):
        self.assertIsInstance(self.instance_default._search_meta.mapping, dict)

    def test_default_mapping_has_the_correct_values(self):
        mapping = self.instance_default._search_meta.mapping
        self.assertDictEqual(mapping['properties']['test_char'], {'type': 'string'})
        self.assertDictEqual(mapping['properties']['test_int'], {'type': 'short'})
        self.assertDictEqual(mapping['properties']['test_float'], {'type': 'double'})
        self.assertDictEqual(mapping['properties']['id'], {'type': 'long'})

    def test_default_2_mapping_is_dictionary(self):
        self.assertIsInstance(self.instance_default_2._search_meta.mapping, dict)

    def test_default_2_mapping_has_the_correct_values(self):
        mapping = self.instance_default_2._search_meta.mapping
        self.assertDictEqual(mapping['properties']['test_int'], {'type': 'short'})
        self.assertDictEqual(mapping['properties']['id'], {'type': 'long'})
        self.assertDictEqual(mapping['properties']['tricky_field'], {'type': 'object'})
        options_passed = self.instance_default_2.__class__.MappingMeta
        expected = options_passed.fields
        expected.extend(options_passed.custom_fields.keys())
        expected.append("id")  # always expect id as it is a necessary field for a mapping
        # but is not added to the django model until its .save() method is called
        self.assertEqual(
            {field.name for field in self.instance_default_2._search_meta.fields},
            set(expected))


@skipUnless(check_connection(), "invalid connection to elasticsearch.")
#@test.modify_settings(ES_INSTALLED_INDICES={"append": ACoolIndex()})
class TestConnecting(ESTestSuite):
    def setUp(self):
        self.elastic = connect()
        self.instance_default = TestModelA(
            test_char="hello, world", test_int=24,
            test_float=3.1415927)
        self.instance_default_2 = TestModelB(
            test_char="hello, world", test_int=24,
            test_float=3.1415927)

        self.aindex = TestModelA._search_meta.index_name
        self.adoctype = TestModelA._search_meta.doctype_name
        self.bindex = TestModelB._search_meta.index_name
        self.bdoctype = TestModelB._search_meta.doctype_name

    def test_creates_alias_by_initializing_model(self):
        self.elastic.indices.exists_alias(name=self.aindex)
        self.elastic.indices.exists_type(index=self.aindex, doc_type=self.adoctype)

        self.elastic.indices.exists_alias(name=self.bindex)
        self.elastic.indices.exists_type(index=self.bindex, doc_type=self.bdoctype)

    def test_saving_instances_automagically(self):
        self.instance_default.save()
        self.assertTrue(self.elastic.exists(index=self.aindex, doc_type=self.adoctype,
            id=self.instance_default.pk))

        self.instance_default_2.save()
        self.assertTrue(self.elastic.exists(index=self.bindex, doc_type=self.bdoctype,
            id=self.instance_default_2.pk))

