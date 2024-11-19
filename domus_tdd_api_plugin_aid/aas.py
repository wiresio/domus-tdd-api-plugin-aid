# -*- coding: utf-8 -*-
from copy import copy
import json
from pathlib import Path
import uuid


from rdflib import Graph
from rdflib.exceptions import ParserError

from tdd.common import (
    frame_nt_content,
    get_id_description,
    put_json_in_sparql,
    put_rdf_in_sparql,
)
from tdd.context import convert_context_to_array, get_context
from tdd.errors import IDMismatchError, JSONDecodeError, RDFValidationError
from tdd.utils import uri_to_base

ONTOLOGY = {"prefix": "aas", "base": "https://admin-shell.io/aas/3/0/"}

DATA_DIR = Path(__file__).parent / "data"

with open(DATA_DIR / "context.v3.json") as fp:
    CONTEXT = json.load(fp)


def validate_aas(str_content, uri=None):
    try:
        json_content = json.loads(str_content)
    except json.decoder.JSONDecodeError as exc:
        raise JSONDecodeError(exc)

    if uri is not None:
        if "id" in json_content:
            if uri != json_content["id"]:
                raise IDMismatchError(json_content["id"], uri)
        else:
            json_content["id"] = uri
    return json_content


def frame_aas_nt_content(uri, nt_content, original_context):
    context = copy(original_context)
    context.append({"@base": uri_to_base(uri)})
    context.append(CONTEXT)

    frame = {
        "@context": context,
        "id": uri,
    }

    str_json_framed = frame_nt_content(nt_content, frame)

    result = json.loads(str_json_framed)
    try:
        del result["@context"]
        del result["@id"]
    except KeyError:
        pass
    return result


def get_aas_description(uri, content_type="application/aas+json"):
    if not content_type.endswith("json"):
        return get_id_description(uri, content_type, ONTOLOGY)
    content = get_id_description(uri, "application/n-triples", ONTOLOGY)
    original_context = get_context(uri, ONTOLOGY)
    jsonld_response = frame_aas_nt_content(uri, content, original_context)
    return jsonld_response


def put_aas_rdf_in_sparql(rdf_content, mimetype, uri=None, delete_if_exists=True):
    g = Graph()
    try:
        g.parse(data=rdf_content, format=mimetype)
    except (SyntaxError, ParserError):
        raise RDFValidationError(f"The RDF triples are not well formatted ({mimetype})")

    put_rdf_in_sparql(
        g,
        uri,
        [CONTEXT],
        delete_if_exists,
        ONTOLOGY,
    )

    return (False, uri)  # For now, updated = False


def put_aas_json_in_sparql(content, uri=None, delete_if_exists=True):
    """
    returns:
    - boolean True if the TD inserted already existed
    - uri of the TD
    """
    content = copy(content)
    convert_context_to_array(content)
    if "id" not in content and "identification" not in content:
        content["id"] = f"urn:uuid:{uuid.uuid4()}"

    original_context = copy(content["@context"])

    uri = uri if uri is not None else content["id"]

    content["@context"].append(CONTEXT)
    content["@context"].append({"@base": uri_to_base(uri)})
    put_json_in_sparql(content, uri, original_context, delete_if_exists, ONTOLOGY)

    return (False, uri)  # For now, updated = False
