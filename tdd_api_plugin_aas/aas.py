# -*- coding: utf-8 -*-
from copy import copy
import json
import re
from pathlib import Path
import uuid
from queue import LifoQueue, Empty

from jinja2 import Environment, FileSystemLoader

from rdflib import Graph, Literal, URIRef, BNode, RDF
from rdflib.exceptions import ParserError

from tdd.common import (
    frame_nt_content,
    get_id_description,
    put_json_in_sparql,
    put_rdf_in_sparql,
)
from tdd.context import convert_context_to_array, get_context
from tdd.errors import IDMismatchError, JSONDecodeError, RDFValidationError
from tdd.registration import delete_registration_information
from tdd.utils import uri_to_base
from tdd.config import CONFIG


VERSION = CONFIG.get("AAS_VERSION", "v3rc02")
BASES = {
    "v3rc01": "https://admin-shell.io/aas/3/0/RC01/",
    "v3rc02": "https://admin-shell.io/aas/3/0/RC02/",
}
ONTOLOGY = {"prefix": "aas", "base": BASES[str(VERSION)]}

AAS_DATA_DIR = Path(__file__).parent / "data" / "aas"

with open(AAS_DATA_DIR / f"context.{VERSION}.json") as fp:
    CONTEXT = json.load(fp)


def validate_aas(str_content, uri=None):
    try:
        json_content = json.loads(str_content)
    except json.decoder.JSONDecodeError as exc:
        raise JSONDecodeError(exc)

    if uri is not None:
        if VERSION == "v3rc01":
            if "identification" in json_content:
                if uri != json_content["identification"]["id"]:
                    raise IDMismatchError(json_content["identification"]["id"], uri)
            else:
                json_content["identification"] = {"id": uri}
        else:
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

    str_json_framed = frame_nt_content(uri, nt_content, frame).decode("utf-8")

    if VERSION == "v3rc01":
        regex = r"(?P<total>\"modelType\"\s*:\s*(?P<class>\"\w+\"))"
        for match in re.finditer(regex, str_json_framed):
            match_dict = match.groupdict()
            str_json_framed = str_json_framed.replace(
                match_dict["total"],
                '"modelType": {\n "name" :' f'{match_dict["class"]}' "\n}",
            )
        str_json_framed = str_json_framed.replace('"urn:XXX:fakeIDToRemove"', "")
        result = json.loads(str_json_framed)
        try:
            node_id = result["id"]
            del result["id"]
            result["identification"] = {
                "id": node_id,
                "idType": "IRI",
            }
        except KeyError:
            pass
    else:
        result = json.loads(str_json_framed)
    try:
        del result["@context"]
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
    if VERSION == "v3rc01":
        str_content = json.dumps(content)
        regex = r"(?P<total>\"modelType\"\s*:\s*\{\s*\"name\"\s*:\s*(?P<class>\"\w+\")\s*\})"
        for match in re.finditer(regex, str_content):
            match_dict = match.groupdict()
            str_content = str_content.replace(
                match_dict["total"], f'"modelType": {match_dict["class"]}'
            )
        if "identification" in content:
            str_content = re.sub(
                r"\"identification\"\s*:\s*\{(?:\s*(?:\"(?:id|idType)\")\s*:\s*\"(?:[^\s]+)\"\s*,?)+\}",  # noqa
                f'"id": "{content["identification"]["id"]}"',
                str_content,
            )
        content = json.loads(str_content)

    uri = uri if uri is not None else content["id"]

    content["@context"].append(CONTEXT)
    content["@context"].append({"@base": uri_to_base(uri)})
    put_json_in_sparql(content, uri, original_context, delete_if_exists, ONTOLOGY)

    return (False, uri)  # For now, updated = False


TYPE_QUERY = """
SELECT ?type WHERE {{
 {NODE} a ?type.
}}
"""

OBJECT_QUERY = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT ?predicate ?object WHERE {{
    {NODE} ?predicate ?object.
    FILTER(?predicate != rdf:type).
}}
"""


ASK_QUERY = """
ASK {{
    {object} ?predicate ?object.
}}
"""

TEMPLATES_ENV = Environment(
    loader=FileSystemLoader(AAS_DATA_DIR / "templates" / VERSION)
)


def get_prefix_header():
    aas_prefix = {"v3rc01": "RC01", "v3rc02": "RC02"}
    return f"""
@prefix aas: <https://admin-shell.io/aas/3/0/{aas_prefix[VERSION]}/>.
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>.
@prefix xsd: <http://www.w3.org/2001/XMLSchema#>.
"""


def id_short(node_id):
    return re.findall(r"(\w+)$", node_id)[0]


def get_xsd_datatype(rdflib_object):
    if type(rdflib_object) == URIRef:
        return "xsd:anyURI"
    elif type(rdflib_object) == Literal and rdflib_object.datatype:
        return rdflib_object.datatype.n3()
    return "xsd:string"


def td_to_aas(uri):
    content = get_id_description(uri, "application/n-triples", {"prefix": "td"})
    g = Graph().parse(data=content, format="nt").skolemize()
    delete_registration_information(uri, g)
    res = f"{get_prefix_header()}\n"

    res += TEMPLATES_ENV.get_template("submodel.jinja2").render(
        submodel=f"<{uri}>",
        id_short=id_short(uri),
    )
    stack = LifoQueue()
    stack.put(URIRef(uri))
    while True:
        try:
            node = stack.get(block=False).n3()
            types = g.objects(URIRef(node), RDF.type)
            # get types of children
            if types:
                for rdf_type in types:
                    res += TEMPLATES_ENV.get_template("element_type.jinja2").render(
                        element=node, rdf_type=rdf_type
                    )
            for result in g.query(OBJECT_QUERY.format(NODE=node)):
                p = getattr(result, "predicate")
                o = getattr(result, "object")
                if not g.query(ASK_QUERY.format(object=o.n3())).askAnswer:
                    res += TEMPLATES_ENV.get_template("qualifier.jinja2").render(
                        element=node,
                        predicate=p,
                        object=o.replace('"', '\\"').replace("\n", " "),
                        object_type=get_xsd_datatype(o),
                    )
                else:
                    stack.put(o)
                    res += TEMPLATES_ENV.get_template("submodelelement.jinja2").render(
                        element=node,
                        value_node=o.n3(),
                        id_short=p.fragment,
                        submodelelement=BNode().n3(),
                        predicate=p,
                        id_short_value=id_short(o),
                    )
        except Empty:
            break
    aas_ntriples = Graph().parse(data=res, format="ttl").serialize(format="nt")
    return put_aas_rdf_in_sparql(
        aas_ntriples, "application/n-triples", uri=uri, delete_if_exists=False
    )
