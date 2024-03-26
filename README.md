# domus-tdd-api-plugin-aid

TDD API AAS Plugin

This is a Plugin for the TDD-API software.
It adds the possibility to handle Asset Interface Descriptions (AIDs).
It can also translate a Thing Description into an AID.

## Plugin installation

To install the plugin, create a Python 3 [virtualenv](https://virtualenv.pypa.io/en/latest/user_guide.html).

```bash
virtualenv env_name
```

Then activate the venv

```bash
source env_name/bin/activate
```

Then install the [domus-tdd-api](https://github.com/eclipse-thingweb/domus-tdd-api).
Finally install this plugin.

You can install from source by cloning this repository

```bash
git clone git@github.com:wiresio/domus-tdd-api-plugin-aid.git
cd domus-tdd-api-plugin-aid
pip install -e .
```

Or you can pip install it from pypi.

```bash
pip install domus-tdd-api-plugin-aid
```

## New routes

- `/aas` : POST an anonymous TD
- `/aas/<ID>` : PUT, DELETE, GET

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
