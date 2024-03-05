import json
import pytest
from pathlib import Path
from jsoncomparison import Compare
from rdflib import Graph
from rdflib.compare import graph_diff


from tdd.tests.conftest import (  # noqa: F401,F811
    SparqlGraph,
    test_client,
    mock_sparql_empty_endpoint,
)

DATA_PATH = Path(__file__).parent / "data"


@pytest.fixture
def mock_sparql_with_one_aid(httpx_mock):
    graph = SparqlGraph("aas/one_aid.trig", format="trig", data_path=DATA_PATH)
    httpx_mock.add_callback(graph.custom)


def assert_graphs_equal(expected_graph, tested_graph):
    _, tested_only, expected_only = graph_diff(tested_graph, expected_graph)
    assert len(tested_only) == 0
    assert len(expected_only) == 0


def test_GET_AAS_OK(test_client, mock_sparql_with_one_aid):  # noqa: F811
    aas_id = "urn:uuid:014139c9-b267-4db5-9c61-cc2d2bfc217d"
    with open(DATA_PATH / "aas" / "one_aid.json") as fp:
        already_present_aas = json.load(fp)
    get_response = test_client.get(f"/aas/{aas_id}")
    assert get_response.status_code == 200
    aas = get_response.json
    diff = Compare().check(already_present_aas, aas)
    assert (
        len(diff) == 1
    )  # XXX For now, we allow one difference: "value" are not exported because empty in rdf in the framed AID


def test_GET_aas_content_negociation(
    test_client, mock_sparql_with_one_aid  # noqa: F811
):
    aas_id = "urn:uuid:014139c9-b267-4db5-9c61-cc2d2bfc217d"
    for mime_type, file_extension in [
        ("text/turtle", "ttl"),
        ("application/rdf+xml", "xml"),
        ("application/n-triples", "nt"),
    ]:
        with open(DATA_PATH / "aas" / f"one_aid.{file_extension}") as fp:
            already_present_aas = fp.read()
        get_response = test_client.get(f"/aas/{aas_id}", headers={"Accept": mime_type})
        assert get_response.status_code == 200
        aas = get_response.get_data()
        g_expected = Graph()
        g_expected.parse(data=already_present_aas, format=mime_type)
        g = Graph()
        g.parse(data=aas, format=mime_type)
        assert_graphs_equal(g, g_expected)


def test_PUT_aas_ok(test_client, mock_sparql_empty_endpoint):  # noqa: F811
    with open(DATA_PATH / "aas" / "one_aid.json") as fp:
        aas_id = "urn:uuid:014139c9-b267-4db5-9c61-cc2d2bfc217d"
        put_response = test_client.put(
            f"/aas/{aas_id}",
            data=fp.read(),
            content_type="application/json",
        )
        assert put_response.status_code == 201
        assert put_response.headers["Location"] == aas_id
        get_response = test_client.get(f"/aas/{aas_id}")
        assert get_response.status_code == 200


def test_POST_aas_ok(test_client, mock_sparql_empty_endpoint):  # noqa: F811
    with open(DATA_PATH / "aas" / "one_aid.json") as fp:
        aas_id = "urn:uuid:014139c9-b267-4db5-9c61-cc2d2bfc217d"
        post_response = test_client.post(
            f"/aas",
            data=fp.read(),
            content_type="application/json",
        )
        assert post_response.status_code == 201
        assert post_response.headers["Location"] == aas_id
        get_response = test_client.get(f"/aas/{aas_id}")
        assert get_response.status_code == 200


def test_PUT_thing_bad_identifier(test_client):  # noqa: F811
    with open(DATA_PATH / "aas" / "one_aid.json") as fp:
        put_response = test_client.put(
            "/aas/urn:test:coucou",
            data=fp.read(),
            content_type="application/json",
        )
        assert put_response.status_code == 400
        assert "'urn:test:coucou' are not compatible" in put_response.json["detail"]


def test_PUT_aas_bad_content_type(test_client):  # noqa: F811
    with open(DATA_PATH / "aas" / "one_aid.json") as fp:
        put_response = test_client.put(
            "/aas/urn:uuid:014139c9-b267-4db5-9c61-cc2d2bfc217d",
            data=fp.read(),
            content_type="text/poulet-xml",
        )
        assert put_response.status_code == 400
        assert "Wrong MimeType" in put_response.json["title"]


def test_DELETE_aas(test_client, mock_sparql_with_one_aid):  # noqa: F811
    """
    Trying: Existing TD in both AAS and TD delete it with /aas
    Expecting:
      - 404 on /aas/aas_id
    """
    aas_id = "urn:uuid:014139c9-b267-4db5-9c61-cc2d2bfc217d"
    get_response = test_client.get(f"/aas/{aas_id}")
    assert get_response.status_code == 200
    test_client.delete(f"/aas/{aas_id}")
    get_aas_response = test_client.get(f"/aas/{aas_id}")
    assert get_aas_response.status_code == 404
