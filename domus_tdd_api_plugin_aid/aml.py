import uuid
import xml.etree.ElementTree as ET
from jinja2 import Environment, FileSystemLoader
from rdflib import Graph

from domus_tdd_api_plugin_aid.aas import DATA_DIR


TEMPLATE_ENV = Environment(loader=FileSystemLoader(str(DATA_DIR / "aml")))


def translate_aml_to_aas(aml_data, uri=None):
    res = """
@prefix aas: <https://admin-shell.io/aas/3/0/>.
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>.
@prefix xsd: <http://www.w3.org/2001/XMLSchema#>.
"""
    id = str(uuid.uuid4())
    if uri is None:
        uri = f"urn:uuid:{id}"
    root = ET.fromstring(aml_data)
    version = 2 if int(root.attrib["SchemaVersion"][0]) >= 3 else 1
    file_name = root.attrib["FileName"]
    res += TEMPLATE_ENV.get_template("aml.jinja2").render(
        identifier=uri, file_name=file_name, version=version
    )
    return uri, Graph().parse(data=res, format="ttl").serialize(format="nt")
