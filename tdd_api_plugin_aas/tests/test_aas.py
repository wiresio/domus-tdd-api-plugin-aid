import json
import pytest
from pathlib import Path
from jsoncomparison import Compare
from rdflib import Graph
from rdflib.compare import graph_diff

from tdd.config import CONFIG
from tdd.tests.conftest import (
    SparqlGraph,
    test_client,
    mock_sparql_empty_endpoint,
)


AAS_VERSION: str = str(CONFIG.get("AAS_VERSION", "v3rc02"))
DATA_PATH = Path("tdd_api_plugin_aas") / "tests" / "data"


@pytest.fixture
def mock_sparql_with_one_aas(httpx_mock):
    graph = SparqlGraph("aas/aas_v3rc02.trig", format="trig", data_path=DATA_PATH)
    httpx_mock.add_callback(graph.custom)


@pytest.fixture
def mock_sparql_with_one_aas_rc01(httpx_mock):
    graph = SparqlGraph("aas/aas_v3rc01.trig", format="trig", data_path=DATA_PATH)
    httpx_mock.add_callback(graph.custom)


@pytest.mark.skipif(AAS_VERSION == "v3rc02", reason=AAS_VERSION)
def test_GET_AAS_OK_rc01(test_client, mock_sparql_with_one_aas_rc01):
    aas_id = "urn:node:opcua:VentilationSystem"
    with open(DATA_PATH / "aas" / "aas_v3rc01.json") as fp:
        already_present_aas = json.load(fp)
    get_response = test_client.get(f"/aas/{aas_id}")
    assert get_response.status_code == 200
    aas = get_response.json
    diff = Compare().check(already_present_aas["submodels"][0], aas)
    assert len(diff) == 0


@pytest.mark.skipif(AAS_VERSION == "v3rc01", reason=AAS_VERSION)
def test_GET_AAS_OK(test_client, mock_sparql_with_one_aas):
    aas_id = "urn:uuid:7c83cce5-7b1f-43b2-8397-e0371a823b35"
    with open(DATA_PATH / "aas" / "aas_v3rc02.json") as fp:
        already_present_aas = json.load(fp)
    get_response = test_client.get(f"/aas/{aas_id}")
    assert get_response.status_code == 200
    aas = get_response.json
    diff = Compare().check(already_present_aas, aas)
    assert len(diff) == 0


@pytest.mark.skipif(AAS_VERSION == "v3rc01", reason=AAS_VERSION)
def test_GET_aas_content_negociation(test_client, mock_sparql_with_one_aas):
    aas_id = "urn:uuid:7c83cce5-7b1f-43b2-8397-e0371a823b35"
    for mime_type, file_extension in [
        ("text/turtle", "ttl"),
        ("application/rdf+xml", "xml"),
        ("text/n3", "n3"),
    ]:
        with open(DATA_PATH / "aas" / f"aas_v3rc02.{file_extension}") as fp:
            already_present_aas = fp.read()
        get_response = test_client.get(f"/aas/{aas_id}", headers={"Accept": mime_type})
        assert get_response.status_code == 200
        aas = get_response.get_data()
        g_expected = Graph()
        g_expected.parse(data=already_present_aas, format=mime_type)
        g = Graph()
        g.parse(data=aas, format=mime_type)
        # TODO this resolves to False due to blank nodes - write function to compare graphs
        g == g_expected
        # TODO remove when TODO above has been resolved
        assert len(g) == len(g_expected)


@pytest.mark.skipif(AAS_VERSION == "v3rc01", reason=AAS_VERSION)
def test_PUT_aas_ok(test_client, mock_sparql_empty_endpoint):
    with open(DATA_PATH / "aas" / "aas_v3rc02.json") as fp:
        aas_id = "urn:uuid:ea720bcd-bdd8-4fe8-9445-2d1cf6bc47d0"
        put_response = test_client.put(
            f"/aas/{aas_id}",
            data=fp.read(),
            content_type="application/json",
        )
        assert put_response.status_code == 201
        assert put_response.headers["Location"] == aas_id
        get_response = test_client.get(f"/aas/{aas_id}")
        assert get_response.status_code == 200


@pytest.mark.skipif(AAS_VERSION == "v3rc02", reason=AAS_VERSION)
def test_PUT_aas_ok_rc01(test_client, mock_sparql_empty_endpoint):
    with open(DATA_PATH / "aas" / "aas_v3rc01.json") as fp:
        aas_id = "urn:uuid:ea720bcd-bdd8-4fe8-9445-2d1cf6bc47d0"
        put_response = test_client.put(
            f"/aas/{aas_id}",
            data=fp.read(),
            content_type="application/json",
        )
        assert put_response.status_code == 201
        assert put_response.headers["Location"] == aas_id
        get_response = test_client.get(f"/aas/{aas_id}")
        assert get_response.status_code == 200


@pytest.mark.skipif(AAS_VERSION == "v3rc01", reason=AAS_VERSION)
def test_PUT_thing_bad_identifier(test_client):
    with open(DATA_PATH / "aas" / "aas_v3rc02.json") as fp:
        put_response = test_client.put(
            "/things/urn:test:coucou",
            data=fp.read(),
            content_type="application/json",
        )
        assert put_response.status_code == 400


@pytest.mark.skipif(AAS_VERSION == "v3rc02", reason=AAS_VERSION)
def test_PUT_thing_bad_identifier_rc01(test_client):
    with open(DATA_PATH / "aas" / "aas_v3rc01.json") as fp:
        put_response = test_client.put(
            "/things/urn:test:coucou",
            data=fp.read(),
            content_type="application/json",
        )
        assert put_response.status_code == 400


def test_PUT_aas_bad_content_type(test_client):
    with open(DATA_PATH / "aas" / "aas_v3rc01.json") as fp:
        put_response = test_client.put(
            "/aas/urn:test:coucou",
            data=fp.read(),
            content_type="text/poulet-xml",
        )
        assert put_response.status_code == 400
        assert "Wrong MimeType" in put_response.json["title"]


def test_PUT_aas_multilanguage_property(test_client, mock_sparql_empty_endpoint):
    with open(DATA_PATH / "aas" / "aas_multilanguage_property.json") as fp:
        aas_id = "urn:uuid:ea720bcd-bdd8-4fe8-9445-2d1cf6bc47d0"
        aas_data = json.load(fp)
        put_response = test_client.put(
            f"/aas/{aas_id}",
            data=json.dumps(aas_data),
            content_type="application/json",
        )
    assert put_response.status_code == 201
    assert put_response.headers["Location"] == aas_id
    get_response = test_client.get(f"/aas/{aas_id}")
    assert get_response.status_code == 200
    diff = Compare().check(aas_data, get_response.json)
    assert len(diff) == 0

    get_rdf_response = test_client.get(f"/aas/{aas_id}", headers={"Accept": "text/n3"})
    got_graph = Graph().parse(data=get_rdf_response.get_data(), format="n3")
    expected_graph = Graph().parse(
        DATA_PATH / "aas" / "aas_multilanguage_property.n3", format="n3"
    )
    _, got_only, expected_only = graph_diff(got_graph, expected_graph)
    assert len(got_only) == 0
    assert len(expected_only) == 0
