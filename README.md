# domus-tdd-api-plugin-aid

TDD API AAS Plugin

This is a Plugin for the TDD-API software.
It adds the possibility to handle Asset Interface Descriptions (AIDs).
It can also translate a Thing Description into an AID.

## Plugin installation

To install the plugin, create a Python 3 [virtualenv](https://virtualenv.pypa.io/en/latest/user_guide.html):

```bash
virtualenv domus
```

Then activate the venv:

```bash
source domus/bin/activate
```

Next install the [domus-tdd-api](https://github.com/eclipse-thingweb/domus-tdd-api):

```bash
git clone https://github.com/eclipse-thingweb/domus-tdd-api.git
cd domus-tdd-api
pip install -e ".[prod]"
npm ci && npm run build
cd ..
```

Then install this plugin. You can install from source by cloning this repository:

```bash
git clone https://github.com/wiresio/domus-tdd-api-plugin-aid.git
cd domus-tdd-api-plugin-aid
pip install -e .
cd ..
```

Or you can `pip install` it from pypi:

```bash
pip install domus-tdd-api-plugin-aid
```

## Testing with example data

Have a fuseki running (and the config.toml/environment variables set to the corresponding SPARQL endpoint).

Install the plugin (see above), then run the TDD API along with the API extension from the installed plugin:

```bash
domus-tdd-api run -p 5050
```

In another terminal in the `domus-tdd-api-plugin-aid` folder

```
curl -XPOST  -iH "Content-Type: application/aml+xml" -d@"./domus_tdd_api_plugin_aid/tests/data/aml/aml_example.xml" http://localhost:5050/aas

```

## New routes

- `/aas` : POST to create an anonymous Asset Administration Shell Object
- `/aas/<ID>` : PUT, DELETE, GET

Accepted mime-types:

- `application/aml+xml`: for AML xml files. They will be translated into AAS objects (AmlBasedSubmodel)
- `application/aas+json` or `application/json`: a JSON AAS file
- RDF mimetypes (`application/rdf+xml`, `text/turtle`, `text/n3`, `application/n-quads`, `application/n-triples`,`application/trig`, `application/ld+json`): a RDF representation in the format corresponding to the mimetype of the AAS object. Using the AAS ontology.

## Data sources

- td-context.ttl: in the transformation, the AID requires short names that
  correspond to those of the TD-JSON documents. We therefore need a RDF version
  of the TD JSON-LD Context.
  This version was retrieved from https://github.com/w3c/wot-thing-description/blob/main/context/td-context.ttl

- context.v3.json: to frame AAS data (an AID) into a correct JSON, we require the
  AAS JSON-LD context. So far, it can be generated with [aas-core-codegen](https://github.com/aas-core-works/aas-core-codegen/tree/main)
  on the latest version of the [aas-core-meta](https://github.com/aas-core-works/aas-core-meta/) repository.
  Run the following command after retrieving both aas-core-codegen and aas-core-meta repository.
  You may need to create an empty snippets directory.

  ```
  aas-core-codegen --model_path <aas-core-meta-folder-path>/aas_core_meta/v3.py --snippets_dir ./jsonld-testing/snippets --output_dir ./jsonld-testing/context --target jsonld

  ```

## Documentation

- AID specification: https://industrialdigitaltwin.org/wp-content/uploads/2024/01/IDTA-02017-1-0_Submodel_Asset-Interfaces-Description.pdf
