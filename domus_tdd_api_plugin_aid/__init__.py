from flask import Blueprint, request, Response
import json

from tdd.common import (
    delete_id,
)
from tdd.utils import (
    POSSIBLE_MIMETYPES,
    negociate_mime_type,
    update_collection_etag,
)
from tdd.errors import WrongMimeType


from domus_tdd_api_plugin_aid.aas import (
    get_aas_description,
    put_aas_json_in_sparql,
    put_aas_rdf_in_sparql,
    validate_aas,
)
from domus_tdd_api_plugin_aid.aml import translate_aml_to_aas

blueprint = Blueprint("domus_tdd_api_plugin_aid", __name__, url_prefix="/aas")


@blueprint.route("/<id>", methods=["DELETE"])
def delete_route_aas(id):
    response = delete_id(id)
    if response.status_code in [200, 204]:
        update_collection_etag()
    return response


@blueprint.route("/<id>", methods=["GET"])
def describe_aas(id):
    mime_type_negociated = negociate_mime_type(
        request, default_mimetype="application/aas+json"
    )
    description = get_aas_description(id, content_type=mime_type_negociated)
    if mime_type_negociated == "application/aas+json":
        description = json.dumps(description)
    return Response(description, content_type=mime_type_negociated)


@blueprint.route("/<id>", methods=["PUT"])
def create_aas(id):
    mimetype = request.content_type
    if mimetype == "application/json":
        mimetype = "application/aas+json"
    if mimetype == "application/aas+json":
        json_ld_content = request.get_data()
        content = validate_aas(json_ld_content, uri=id)
        updated, uri = put_aas_json_in_sparql(content, uri=id)
    elif mimetype == "application/aml+xml":
        aml_data = request.get_data()
        rdf_aas_data = translate_aml_to_aas(aml_data)
        updated, uri = put_aas_rdf_in_sparql(rdf_aas_data, "application/n-triples")
    elif mimetype in POSSIBLE_MIMETYPES:
        rdf_content = request.get_data()
        updated, uri = put_aas_rdf_in_sparql(rdf_content, mimetype)
    else:
        raise WrongMimeType(mimetype)

    update_collection_etag()
    return Response(status=201 if not updated else 204, headers={"Location": uri})


@blueprint.route("", methods=["POST"])
def create_anonymous_aas():
    mimetype = request.content_type
    if mimetype == "application/json":
        mimetype = "application/aas+json"
    if mimetype == "application/aas+json":
        json_ld_content = request.get_data()
        content = validate_aas(json_ld_content)
        updated, uri = put_aas_json_in_sparql(content, delete_if_exists=False)
    elif mimetype == "application/aml+xml":
        aml_data = request.get_data()
        rdf_aas_data = translate_aml_to_aas(aml_data)
        updated, uri = put_aas_rdf_in_sparql(rdf_aas_data, "application/n-triples")
    elif mimetype in POSSIBLE_MIMETYPES:
        content = request.get_data()
        updated, uri = put_aas_rdf_in_sparql(content, mimetype, delete_if_exists=False)
    else:
        raise WrongMimeType(mimetype)
    update_collection_etag()
    return Response(status=201 if not updated else 204, headers={"Location": uri})
