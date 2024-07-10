from tdd.tests.conftest import (  # noqa: F401,F811
    SparqlGraph,
    test_client,
    mock_sparql_empty_endpoint,
)

from domus_tdd_api_plugin_aid.tests.test_aid import DATA_PATH


def test_PUT_aml_ok(test_client, mock_sparql_empty_endpoint):  # noqa: F811
    with open(DATA_PATH / "aas" / "aml_example.xml") as fp:
        aas_id = "urn:poulet"
        put_response = test_client.put(
            f"/aas/{aas_id}",
            data=fp.read(),
            content_type="application/aml+xml",
        )
        assert put_response.status_code == 201
        assert put_response.headers["Location"] == aas_id
        get_response = test_client.get(f"/aas/{aas_id}")
        assert get_response.status_code == 200


def test_POST_aml_ok(test_client, mock_sparql_empty_endpoint):  # noqa: F811
    with open(DATA_PATH / "aas" / "aml_example.xml") as fp:
        put_response = test_client.post(
            f"/aas",
            data=fp.read(),
            content_type="application/aml+xml",
        )
        assert put_response.status_code == 201
        assert put_response.headers["Location"] is not None
        get_response = test_client.get(f'/aas/{ put_response.headers["Location"]}')
        assert get_response.status_code == 200