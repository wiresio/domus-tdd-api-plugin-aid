import re

from queue import LifoQueue, Empty

from jinja2 import Environment, FileSystemLoader
from rdflib import Graph, Literal, URIRef, BNode
from tdd.common import get_id_description
from tdd.registration import delete_registration_information


from domus_tdd_api_plugin_aid.aas import DATA_DIR, put_aas_rdf_in_sparql

TD_CONTEXT_GRAPH = Graph().parse(DATA_DIR / "td-context.ttl", format="ttl")

TEMPLATE_ENV = Environment(loader=FileSystemLoader(str(DATA_DIR / "aid")))

PROPERTIES_NOT_EXPORTED = [
    "https://www.w3.org/2019/wot/td#hasEventAffordance",
    "https://www.w3.org/2019/wot/td#hasActionAffordance",
    "https://www.w3.org/2019/wot/td#hasPropertyAffordance",
    "https://www.w3.org/2019/wot/td#description",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
]

PROPERTIES_ON_PROTOCOL_INTERFACE = [
    "https://www.w3.org/2019/wot/td#title",
    "http://purl.org/dc/terms/created",
    "http://purl.org/dc/terms/modified",
    "https://www.w3.org/2019/wot/td#supportContact",
]

TYPE_QUERY = """
SELECT ?type WHERE {{
 {NODE} a ?type.
}}
"""


GET_PROTOCOLS_QUERY = """
PREFIX td: <https://www.w3.org/2019/wot/td#>
PREFIX hctl: <https://www.w3.org/2019/wot/hypermedia#>

SELECT DISTINCT ?protocol
WHERE {
  ?Thing td:hasPropertyAffordance ?Prop.
  ?Prop td:hasForm ?Form.
  ?Form hctl:hasTarget ?URL.
  BIND (STRBEFORE(str(?URL), "://") AS ?protocol)
}
"""

GET_PROPERTIES_ROOT_NODE = """
PREFIX td: <https://www.w3.org/2019/wot/td#>
PREFIX hctl: <https://www.w3.org/2019/wot/hypermedia#>

SELECT DISTINCT ?Prop ?name
WHERE {{
  ?Thing td:hasPropertyAffordance ?Prop.
  ?Prop td:hasForm ?Form.
  ?Form hctl:hasTarget ?URL.
  FILTER (STRSTARTS(str(?URL), "{protocol}"))
  OPTIONAL {{
   ?Prop td:name ?name
  }}
}}
"""

THING_QUERY = """
PREFIX td: <https://www.w3.org/2019/wot/td#>

SELECT DISTINCT ?thing
WHERE {
  ?thing a td:Thing
}
"""

GET_PROPERTY_VALUE = """
SELECT ?value WHERE {{

{NODE} <{property}> ?value

}}
"""

GET_SHORT_ID = """
PREFIX jsonld: <http://www.w3.org/ns/json-ld#>
SELECT DISTINCT ?idShort WHERE {{
 ?x jsonld:term ?idShort .
 ?x jsonld:iri <{full_uri}>.
}}
"""


PREFIX_HEADER = """
@prefix aas: <https://admin-shell.io/aas/3/0/>.
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>.
@prefix xsd: <http://www.w3.org/2001/XMLSchema#>.
"""


def id_short(node_id):
    id_shorts = [
        x[0] for x in TD_CONTEXT_GRAPH.query(GET_SHORT_ID.format(full_uri=node_id))
    ]
    if id_shorts:
        return id_shorts[0]

    return re.findall(r"(\w+)$", node_id)[0]


def get_description(aid_node, td_node, g):
    descriptions_values = [
        v
        for (_s, _p, v) in g.triples(
            (td_node, URIRef("https://www.w3.org/2019/wot/td#description"), None)
        )
    ]
    if not descriptions_values:
        return ""

    return TEMPLATE_ENV.get_template("description.jinja2").render(
        aid_uri=aid_node,
        language=descriptions_values[0].language,
        text=descriptions_values[0].value,
    )


def get_xsd_datatype(rdflib_object):
    if isinstance(rdflib_object, URIRef):
        return "xsd:anyURI"
    elif isinstance(rdflib_object, Literal) and rdflib_object.datatype:
        return rdflib_object.datatype.n3()
    return "xsd:string"


def dfs(root_nodes_pair, g, skipped_properties=[]):
    """
    root_nodes: (td_node (in RDF Form: BNode, URIRef, etc.), aid_node: str)

    """
    stack = LifoQueue()
    stack.put(root_nodes_pair)
    res = ""
    while True:
        try:
            node_td, node_aid = stack.get(block=False)
            triples = [
                (p, o)
                for (s, p, o) in g.triples((node_td, None, None))
                if str(p) not in skipped_properties
            ]
            for p, o in triples:
                object_triples = [x for x in g.triples((o, None, None))]
                if len(object_triples) == 0:
                    res += TEMPLATE_ENV.get_template("property.jinja2").render(
                        element=node_aid,
                        predicate_id_short=id_short(p),
                        object=o.replace('"', '\\"'),
                        object_type=get_xsd_datatype(o),
                        predicate=p,
                    )
                else:
                    submodel_element_collection_bnode = BNode().n3()
                    stack.put((o, submodel_element_collection_bnode))
                    res += (
                        f"{node_aid} "
                        "<https://admin-shell.io/aas/3/0/SubmodelElementCollection/value> "
                        f"{submodel_element_collection_bnode}.\n"
                    )

                    res += TEMPLATE_ENV.get_template(
                        "submodel_element_collection.jinja2"
                    ).render(
                        id_short=id_short(p),
                        submodelelement_uri=submodel_element_collection_bnode,
                        predicate=p,
                    )
        except Empty:
            break
    return res


def interface_protocol_rdf(interface_protocol_uri, root_node_uri, g, protocol):
    """
    Retrieves data on the TD root node
    exports it as submodel for the interfaceXXX
    protocol node
    """
    res = ""

    # Properties to export directly on InterfaceXXX node
    for prop in PROPERTIES_ON_PROTOCOL_INTERFACE:
        values = [
            x[0]
            for x in g.query(
                GET_PROPERTY_VALUE.format(NODE=root_node_uri.n3(), property=prop)
            )
        ]
        if len(values) > 1:
            print(f"Multiple values for {prop}: {', '.join(values)}")
            continue
        if len(values) == 0:
            continue
        value = values[0]
        res += TEMPLATE_ENV.get_template("property.jinja2").render(
            element=interface_protocol_uri,
            predicate_id_short=id_short(prop),
            predicate=prop,
            object=value.replace('"', '\\"'),
            object_type=get_xsd_datatype(value),
        )
    # EndpointMetadata
    # Every property except those in PROPERTIES_NOT_EXPORTED and PROPERTIES_ON_PROTOCOL_INTERFACE
    endpoint_metadata_bnode = BNode().n3()
    res += (
        f"{interface_protocol_uri} "
        "<https://admin-shell.io/aas/3/0/SubmodelElementCollection/value> "
        f"{endpoint_metadata_bnode}.\n"
    )
    res += TEMPLATE_ENV.get_template("submodel_element_collection.jinja2").render(
        id_short="EndpointMetadata",
        submodelelement_uri=endpoint_metadata_bnode,
        predicate="https://admin-shell.io/idta/AssetInterfacesDescription/1/0/EndpointMetadata",
    )
    res += dfs(
        (root_node_uri, endpoint_metadata_bnode),
        g,
        skipped_properties=PROPERTIES_NOT_EXPORTED + PROPERTIES_ON_PROTOCOL_INTERFACE,
    )

    # InteractionMetadata
    interaction_metadata_bnode = BNode().n3()
    res += (
        f"{interface_protocol_uri} "
        "<https://admin-shell.io/aas/3/0/SubmodelElementCollection/value> "
        f"{interaction_metadata_bnode}.\n"
    )
    res += TEMPLATE_ENV.get_template("submodel_element_collection.jinja2").render(
        id_short="InteractionMetadata",
        submodelelement_uri=interaction_metadata_bnode,
        predicate="https://admin-shell.io/idta/AssetInterfacesDescription/1/0/InteractionMetadata",
    )
    # Get properties Node
    properties_bnode = BNode().n3()
    res += (
        f"{interaction_metadata_bnode} "
        "<https://admin-shell.io/aas/3/0/SubmodelElementCollection/value> "
        f"{properties_bnode}.\n"
    )
    res += TEMPLATE_ENV.get_template("submodel_element_collection.jinja2").render(
        id_short="properties",
        submodelelement_uri=properties_bnode,
        predicate="https://www.w3.org/2019/wot/td#PropertyAffordance",
    )

    for property_node, property_name in g.query(
        GET_PROPERTIES_ROOT_NODE.format(protocol=protocol)
    ):
        property_bnode = BNode().n3()
        res += (
            f"{properties_bnode} "
            "<https://admin-shell.io/aas/3/0/SubmodelElementCollection/value> "
            f"{property_bnode}.\n"
        )
        res += get_description(property_bnode, property_node, g)
        res += TEMPLATE_ENV.get_template("submodel_element_collection.jinja2").render(
            id_short=property_name,
            submodelelement_uri=property_bnode,
            predicate="https://admin-shell.io/idta/AssetInterfaceDescription/1/0/PropertyDefinition",  # noqa
        )
        res += dfs(
            (property_node, property_bnode),
            g,
            skipped_properties=["https://www.w3.org/2019/wot/td#name"]
            + PROPERTIES_NOT_EXPORTED,
        )
    # Actions
    actions_bnode = BNode().n3()
    res += (
        f"{interaction_metadata_bnode} "
        "<https://admin-shell.io/aas/3/0/SubmodelElementCollection/value> "
        f"{actions_bnode}.\n"
    )
    res += TEMPLATE_ENV.get_template("submodel_element_collection.jinja2").render(
        id_short="actions",
        submodelelement_uri=actions_bnode,
        predicate="https://www.w3.org/2019/wot/td#ActionAffordance",
    )
    # Events
    events_bnode = BNode().n3()
    res += (
        f"{interaction_metadata_bnode} "
        "<https://admin-shell.io/aas/3/0/SubmodelElementCollection/value> "
        f"{events_bnode}.\n"
    )
    res += TEMPLATE_ENV.get_template("submodel_element_collection.jinja2").render(
        id_short="events",
        submodelelement_uri=events_bnode,
        predicate="https://www.w3.org/2019/wot/td#EventAffordance",
    )
    return res


def td_to_aas(uri):
    content = get_id_description(uri, "application/n-triples", {"prefix": "td"})
    content = content.replace(r"\n", "###LINEBREAK###")
    g = Graph().parse(data=content, format="nt").skolemize()
    delete_registration_information(uri, g)

    root_node_uri = [x[0] for x in g.query(THING_QUERY)][0]
    root_node = root_node_uri.n3()
    res = f"{PREFIX_HEADER}\n"

    res += TEMPLATE_ENV.get_template("aid.jinja2").render(
        submodel=root_node,
        aid_id=uri,
        id_short=id_short(root_node_uri),
    )
    res += TEMPLATE_ENV.get_template("semantic_id.jinja2").render(
        element=root_node,
        uri="https://admin-shell.io/idta/AssetInterfacesDescription/1/0/Submodel",
    )
    res += get_description(root_node, root_node_uri, g)

    protocols = [x[0] for x in g.query(GET_PROTOCOLS_QUERY)]

    for protocol in protocols:
        interface_protocol_name = f"Interface{protocol.upper()}"
        interface_protocol_uri = f"_:b{interface_protocol_name}"
        res += TEMPLATE_ENV.get_template("aid_to_submodel_element.jinja2").render(
            submodel=root_node,
            interface=interface_protocol_uri,
        )
        res += TEMPLATE_ENV.get_template("submodel_element_collection.jinja2").render(
            id_short=interface_protocol_name,
            submodelelement_uri=interface_protocol_uri,
            predicate="https://admin-shell.io/idta/AssetInterfacesDescription/1/0/Interface",
        )
        res += interface_protocol_rdf(
            interface_protocol_uri, root_node_uri, g, protocol
        )
    
    res = res.replace("###LINEBREAK###", "\\n")
    aas_ntriples = Graph().parse(data=res, format="ttl").serialize(format="nt")
    return put_aas_rdf_in_sparql(
        aas_ntriples, "application/n-triples", uri=uri, delete_if_exists=False
    )
