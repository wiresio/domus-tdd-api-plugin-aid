import xml.etree.ElementTree as ET
from jinja2 import Environment, FileSystemLoader

from domus_tdd_api_plugin_aid.aas import DATA_DIR


TEMPLATE_ENV = Environment(loader=FileSystemLoader(str(DATA_DIR / "aml")))


def translate_aml_to_aas(aml_data):
    root = ET.fromstring(aml_data)
    version = root.attrib["SchemaVersion"]
    file_name = root.attrib["FileName"]
    print("poulet", version, file_name)
