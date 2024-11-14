import json
import pytest

from jsoncomparison import Compare

from tdd import CONFIG
from tdd.tests.conftest import (  # noqa: F401,F811
    assert_only_on_known_errors,
    SparqlGraph,
    test_client,
    mock_sparql_empty_endpoint,
)

from domus_tdd_api_plugin_aid.tests.test_aid import DATA_PATH

CONFIG["LIMIT_BATCH_TDS"] = 15
CONFIG["CHECK_SCHEMA"] = True
CONFIG["PERIOD_CLEAR_EXPIRE_TD"] = 0
CONFIG["OVERWRITE_DISCOVERY"] = True


@pytest.fixture
def mock_sparql_aas_and_td(httpx_mock):
    graph = SparqlGraph("td-to-aas/td_aas.trig", format="trig", data_path=DATA_PATH)
    httpx_mock.add_callback(graph.custom)


def test_POST_td(test_client, mock_sparql_empty_endpoint):  # noqa: F811
    """
    Trying: post a TD on /things
    Expecting:
      - TD retrievable as TD on /things
      - TD retrievable as AAS on /aas
    """
    with open(DATA_PATH / "td-to-aas" / "mylamp.td.json") as fp:
        data = fp.read()
        uri = "urn:uuid:0804d572-cce8-422a-bb7c-4412fcd56f06"
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
    with open(DATA_PATH / "td-to-aas" / "mylamp.aid.json") as fp:
        aas = aas_response.json
        target_aas = json.load(fp)
        diff = Compare().check(target_aas, aas)
        assert (
            diff == {}
        )  # FIXME: some fine-tuning to do. Must look at what fields are mandatory to express


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
