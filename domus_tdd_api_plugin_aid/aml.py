import uuid
import xml.etree.ElementTree as ET
from jinja2 import Environment, FileSystemLoader
from rdflib import Graph

from tdd.errors import IDMismatchError, AppException


from domus_tdd_api_plugin_aid.aas import DATA_DIR
from domus_tdd_api_plugin_aid.errors import AMLDecodeError


TEMPLATE_ENV = Environment(loader=FileSystemLoader(str(DATA_DIR / "aml")))


def translate_aml_to_aas(aml_data, uri=None):
    res = """
@prefix aas: <https://admin-shell.io/aas/3/0/>.
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>.
@prefix xs: <http://www.w3.org/2001/XMLSchema#>.
@prefix xsd: <http://www.w3.org/2001/XMLSchema#>.

"""
    xmlns = {"": "http://www.dke.de/CAEX"}
    try:
        root = ET.fromstring(aml_data)
    except Exception as exc:
        raise AMLDecodeError(exc)
    version = 2 if int(root.attrib["SchemaVersion"][0]) >= 3 else 1
    file_name = root.attrib["FileName"]

    # Create a AAS object
    project = root.find("./InstanceHierarchy/InternalElement", xmlns)
    if project is None:
        raise AppException(
            'No project found, make sure you have the correct xmlns="http://www.dke.de/CAEX" in your XML root element'
        )
    project_id = project.attrib.get("ID", None)
    if uri is not None:
        if project_id is not None:
            if uri != f"urn:aml:{project_id}":
                raise IDMismatchError(f"urn:aml:{project_id}", uri)
        else:
            project_id = uri
    else:
        if project_id is None:
            project_id = str(uuid.uuid4())
        uri = f"urn:aml:{project_id}"

    res += TEMPLATE_ENV.get_template("root.jinja2").render(identifier=project_id)

    # get all devices
    for device in project.iterfind("InternalElement", xmlns):
        # each device will implement the aml.jinja2 template
        aid_id = device.attrib.get("ID", str(uuid.uuid4()))
        res += TEMPLATE_ENV.get_template("aml.jinja2").render(
            identifier=aid_id,
            file_name=file_name,
            version=version,
            project_id=project_id,
        )
        # find each element
        attributes_and_interfaces = {}
        for element in device.iterfind("InternalElement", xmlns):

            name = element.attrib["Name"]
            element_id = element.attrib.get("ID", str(uuid.uuid4()))
            # if element has ExternalInterface, then export it
            interface = element.find("ExternalInterface", xmlns)
            if interface is None:
                continue

            data_value = None
            datatype = None
            dataname = None
            for attribute in element.iterfind("Attribute", xmlns):
                if attribute.attrib["Name"] in ["Name", "ID"]:
                    continue
                data_value = attribute.find("Value", xmlns).text
                datatype = attribute.attrib["AttributeDataType"]
                dataname = attribute.attrib["Name"]

            try:
                interface_uri = (
                    interface.find("Attribute[@Name='refURI']", xmlns)
                    .find("Value", xmlns)
                    .text
                )
            except Exception:
                interface_uri = None
            interface_name = interface.attrib["Name"]
            attributes_and_interfaces[name] = {
                "id": element_id,
                "value": data_value,
                "datatype": datatype,
                "uri": interface_uri,
                "interface_name": interface_name,
                "data_name": dataname,
            }
        if attributes_and_interfaces:
            # implement an AttributeContainer
            # put each interface in the container
            entities_list_exported = False
            for entity_name, attribute in attributes_and_interfaces.items():
                relevant = False
                if attribute["data_name"] is not None:
                    res += TEMPLATE_ENV.get_template("value_attribute.jinja2").render(
                        identifier=attribute["id"],
                        data_value=attribute["value"],
                        dataname=attribute["data_name"],
                        datatype=attribute["datatype"],
                        submodel_id=aid_id,
                    )
                    relevant = True
                if attribute["uri"] is not None:
                    res += TEMPLATE_ENV.get_template("value_attribute.jinja2").render(
                        identifier=attribute["id"],
                        data_value=attribute["uri"],
                        dataname="refURI",
                        datatype="xs:string",
                        submodel_id=aid_id,
                    )
                    relevant = True
                if relevant:
                    if not entities_list_exported:
                        res += TEMPLATE_ENV.get_template("entities_list.jinja2").render(
                            submodel_id=aid_id
                        )
                        entities_list_exported = True
                    res += TEMPLATE_ENV.get_template("entity_export.jinja2").render(
                        submodel_id=aid_id,
                        entity_id=attribute["id"],
                        entity_name=entity_name,
                    )

    return uri, Graph().parse(data=res, format="ttl").serialize(format="nt")
