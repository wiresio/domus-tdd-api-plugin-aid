from flask import Blueprint, request, Response
import json

from tdd.common import (
    delete_id,
    get_check_schema_from_url_params,
)
from tdd.utils import (
    POSSIBLE_MIMETYPES,
    negociate_mime_type,
    update_collection_etag,
)
from tdd.errors import WrongMimeType

from tdd_api_plugin_aas.aas import (
    get_aas_description,
    put_aas_json_in_sparql,
    put_aas_rdf_in_sparql,
    validate_aas,
)

blueprint = Blueprint('tdd_api_plugin_aas', __name__, url_prefix="/aas")

@blueprint.route("/aas/<id>", methods=["DELETE"])
def delete_route_aas(id):
    response = delete_id(id)
    if response.status_code in [200, 204]:
        update_collection_etag()
    return response

@blueprint.route("/aas/<id>", methods=["GET"])
def describe_aas(id):
    mime_type_negociated = negociate_mime_type(
        request, default_mimetype="application/aas+json"
    )
    description = get_aas_description(id, mime_type_negociated)
    if mime_type_negociated == "application/aas+json":
        description = json.dumps(description)
    return Response(description, content_type=mime_type_negociated)

@blueprint.route("/aas/<id>", methods=["PUT"])
def create_aas(id):
    mimetype = request.content_type
    check_schema = get_check_schema_from_url_params(request)
    if mimetype == "application/json":
        mimetype = "application/aas+json"
    if mimetype == "application/aas+json":
        json_ld_content = request.get_data()
        content = validate_aas(json_ld_content, uri=id, check_schema=check_schema)
        updated, uri = put_aas_json_in_sparql(content, uri=id)
    elif mimetype in POSSIBLE_MIMETYPES:
        rdf_content = request.get_data()
        updated, uri = put_aas_rdf_in_sparql(rdf_content, mimetype)
    else:
        raise WrongMimeType(mimetype)

    update_collection_etag()
    return Response(status=201 if not updated else 204, headers={"Location": uri})

@blueprint.route("/aas", methods=["POST"])
def create_anonymous_aas():
    mimetype = request.content_type
    check_schema = get_check_schema_from_url_params(request)
    if mimetype == "application/json":
        mimetype = "application/aas+json"
    if mimetype == "application/aas+json":
        json_ld_content = request.get_data()
        content = validate_aas(json_ld_content, check_schema=check_schema)
        updated, uri = put_aas_json_in_sparql(content, delete_if_exists=False)
    elif mimetype in POSSIBLE_MIMETYPES:
        content = request.get_data()
        updated, uri = put_aas_rdf_in_sparql(
            content, mimetype, delete_if_exists=False
        )
    else:
        raise WrongMimeType(mimetype)
    update_collection_etag()
    return Response(status=201 if not updated else 204, headers={"Location": uri})
