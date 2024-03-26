import json
import pytest
import re
from mock import patch

from jsoncomparison import Compare

from tdd import CONFIG
from tdd.tests.conftest import (  # noqa: F401,F811
    assert_only_on_known_errors,
    SparqlGraph,
    test_client,
    mock_sparql_empty_endpoint,
)

from tdd_api_plugin_aas.tests.test_aas import AAS_VERSION, DATA_PATH

CONFIG["LIMIT_BATCH_TDS"] = 15
CONFIG["CHECK_SCHEMA"] = True
CONFIG["PERIOD_CLEAR_EXPIRE_TD"] = 0
CONFIG["OVERWRITE_DISCOVERY"] = True


def remove_skolemized_blank_node_values(json_str):
    json_str = re.sub(r"https?\:\/\/rdf?lib[^\"]+", "", json_str)
    json_str = re.sub(r"\"idShort\": \"[^\"]+\"", '"idShort": ""', json_str)
    return json.loads(json_str)


@pytest.fixture
def mock_sparql_aas_and_td(httpx_mock):
    graph = SparqlGraph("td-to-aas/td_aas.trig", format="trig", data_path=DATA_PATH)
    httpx_mock.add_callback(graph.custom)


@pytest.mark.skipif(AAS_VERSION == "v3rc01", reason=AAS_VERSION)
def test_POST_td_v3rc02(test_client, mock_sparql_empty_endpoint):  # noqa: F811
    """
    Trying: post a TD on /things
    Expecting:
      - TD retrievable as TD on /things
      - TD retrievable as AAS on /aas
    """
    with open(DATA_PATH / "td-to-aas" / "small-td.json") as fp:
        data = fp.read()
        uri = "urn:illuminance:sensor"
        post_response = test_client.post(
            "/things", data=data, content_type="application/json"
        )
        assert post_response.status_code == 201
        assert post_response.headers["Location"] == uri
    td_response = test_client.get(f"/things/{uri}")
    assert td_response.status_code == 200
    td = td_response.json
    del td["registration"]
    diff = Compare().check(json.loads(data), td)
    assert_only_on_known_errors(diff)

    aas_response = test_client.get(f"/aas/{uri}")
    assert aas_response.status_code == 200
    with open(DATA_PATH / "td-to-aas" / "aas-v3rc02.json") as fp:
        aas = remove_skolemized_blank_node_values(json.dumps(aas_response.json))
        target_aas = remove_skolemized_blank_node_values(fp.read())
        diff = Compare().check(target_aas, aas)
        assert diff == {}


@pytest.mark.skipif(AAS_VERSION == "v3rc02", reason=AAS_VERSION)
@patch("tdd.tests.conftests.mock_sparql_empty_endpoint")
def test_POST_td_v3rc01(test_client, mock_sparql_empty_endpoint):  # noqa: F811
    """
    Trying: post a TD on /things
    Expecting:
      - TD retrievable as TD on /things
      - TD retrievable as AAS on /aas
    """
    with open(DATA_PATH / "td-to-aas" / "small-td.json") as fp:
        data = fp.read()
        uri = "urn:illuminance:sensor"
        post_response = test_client.post(
            "/things", data=data, content_type="application/json"
        )
        assert post_response.status_code == 201
        assert post_response.headers["Location"] == uri
    td_response = test_client.get(f"/things/{uri}")
    assert td_response.status_code == 200
    td = td_response.json
    del td["registration"]
    diff = Compare().check(json.loads(data), td)
    assert_only_on_known_errors(diff)

    aas_response = test_client.get(f"/aas/{uri}")
    assert aas_response.status_code == 200
    with open(DATA_PATH / "td-to-aas" / "aas-v3rc01.json") as fp:
        aas = remove_skolemized_blank_node_values(json.dumps(aas_response.json))
        target_aas = remove_skolemized_blank_node_values(fp.read())
        diff = Compare().check(target_aas, aas)
        assert diff == {}


def test_DELETE_things(test_client, mock_sparql_aas_and_td):  # noqa: F811
    """
    Trying: Existing TD in both AAS and TD delete it with /things
    Expecting:
      - 404 on /things/uri
      - 404 on /aas/uri
    """
    uri = "urn:illuminance:sensor"
    get_response = test_client.get(f"/things/{uri}")
    assert get_response.status_code == 200
    get_aas_response = test_client.get(f"/aas/{uri}")
    assert get_aas_response.status_code == 200
    test_client.delete(f"/things/{uri}")
    get_response = test_client.get(f"/things/{uri}")
    assert get_response.status_code == 404
    get_aas_response = test_client.get(f"/aas/{uri}")
    assert get_aas_response.status_code == 404


def test_DELETE_aas(test_client, mock_sparql_aas_and_td):  # noqa: F811
    """
    Trying: Existing TD in both AAS and TD delete it with /aas
    Expecting:
      - 404 on /things/uri
      - 404 on /aas/uri
    """
    uri = "urn:illuminance:sensor"
    get_response = test_client.get(f"/things/{uri}")
    assert get_response.status_code == 200
    get_aas_response = test_client.get(f"/aas/{uri}")
    assert get_aas_response.status_code == 200
    test_client.delete(f"/aas/{uri}")
    get_response = test_client.get(f"/things/{uri}")
    assert get_response.status_code == 404
    get_aas_response = test_client.get(f"/aas/{uri}")
    assert get_aas_response.status_code == 404
