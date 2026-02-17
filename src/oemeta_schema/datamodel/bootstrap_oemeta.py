import yaml
import requests
import json
from rdflib import Graph
import os

SCHEMA_URL = "https://raw.githubusercontent.com/OpenEnergyPlatform/oemetadata/production/oemetadata/v2/v20/schema.json"
OUTPUT_YAML = "src/oemeta_schema/schema/oemetadata_sem.yaml"
OUTPUT_VOCAB = "src/oemeta_schema/schema/oemetadata_vocabulary.jsonld"

OEP_MAPPING = {
    # (Existing mapping dictionary remains the same)
    "name": "rdfs:label", "title": "dct:title", "description": "dct:description",
    "@id": "dct:identifier", "resources": "dcat:Dataset", "topics": "foaf:topic",
    "path": "dcat:accessURL", "languages": "dct:language", "keywords": "dcat:keyword",
    "publicationDate": "dct:issued", "embargoPeriod": "adms:status", "start": "dbo:startDateTime",
    "end": "dbo:endDateTime", "isActive": "adms:status", "homepage": "foaf:homepage",
    "documentation": "ncit:Project_Description", "sourceCode": "oeo:code_source",
    "publisher": "dct:publisher", "publisherLogo": "foaf:logo", "contact": "oeo:contact_person",
    "fundingAgency": "sc:FundingAgency", "fundingAgencyLogo": "foaf:logo", "grantNo": "sc:Grant",
    "location": "dct:location", "address": "schema:address", "latitude": "schema:latitude",
    "longitude": "schema:longitude", "extent": "oeo:spatial_region",
    "resolutionValue": "dcat:spatialResolutionInMeters", "resolutionUnit": "oeo:unit",
    "boundingBox": "dcat:bbox", "crs": "cco:GeospatialCoordinateReferenceSystem",
    "temporal": "schema:temporalCoverage", "referenceDate": "dct:date", "timeseries": "dct:PeriodOfTime",
    "sources": "dct:source", "authors": "oeo:author", "publicationYear": "dct:issued",
    "sourceLicenses": "dct:license", "instruction": "rdfs:comment", "attribution": "ms:copyright_notice",
    "unit": "oeo:OEO_00010045", "value": "rdf:value", "primaryKey": "csvw:primaryKey",
    "foreignKeys": "csvw:foreignKey", "delimiter": "csvw:delimiter"
}


def generate_vocabulary(yaml_path, output_path):
    """Generates a Vocabulary definition (RDF Schema) in JSON-LD with an explicit @graph."""
    print(f"Generating Vocabulary Definition (RDF Schema)...")

    # 1. Generate OWL/RDF using LinkML's OwlSchemaGenerator
    from linkml.generators.owlgen import OwlSchemaGenerator
    owl_gen = OwlSchemaGenerator(yaml_path)
    owl_graph_str = owl_gen.serialize()

    # 2. Parse into RDFLib
    g = Graph()
    g.parse(data=owl_graph_str, format="turtle")

    # 3. Serialize to JSON-LD
    # 'compact' or 'flattened' usually provides the cleanest @graph structure
    context = {
        "oep": "https://openenergyplatform.org/metadata/v20/",
        "oeo": "http://openenergyontology.org/ontology/",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "owl": "http://www.w3.org/2002/07/owl#",
        "skos": "http://www.w3.org/2004/02/skos/core#"
    }

    # We serialize to a dict first to manipulate it
    expanded = json.loads(g.serialize(format='json-ld'))

    # Force the @graph envelope
    vocab_jsonld = {
        "@context": context,
        "@graph": expanded
    }

    with open(output_path, "w") as f:
        json.dump(vocab_jsonld, f, indent=4)

    print(f"Vocabulary Definition with @graph saved to: {output_path}")

def bootstrap():
    response = requests.get(SCHEMA_URL)
    jsonschema = response.json()

    linkml = {
        "id": "https://openenergyplatform.org/metadata/v20",
        "name": "oemetadata_v20",
        "imports": ["linkml:types"],
        "prefixes": {
            "linkml": "https://w3id.org/linkml/",
            "oep": "https://openenergyplatform.org/metadata/v20/",
            "oeo": "http://openenergyontology.org/ontology/",
            "schema": "http://schema.org/",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "dct": "http://purl.org/dc/terms/",
            "dcat": "http://www.w3.org/ns/dcat#",
            "foaf": "http://xmlns.com/foaf/0.1/",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "adms": "http://www.w3.org/ns/adms#",
            "dbo": "http://dbpedia.org/ontology/",
            "ncit": "http://purl.obolibrary.org/obo/NCIT_",
            "sc": "http://schema.org/",
            "cco": "http://www.ontologyrepository.com/CommonCoreOntologies/",
            "csvw": "http://www.w3.org/ns/csvw#",
            "ms": "http://purl.org/net/ms-ontology#"
        },
        "default_prefix": "oep",
        "default_range": "string",
        "classes": {},
        "slots": {},
        "enums": {}
    }

    def extract_enum(prop_name, details):
        enum_values = details.get("enum")
        if not enum_values and "items" in details:
            enum_values = details["items"].get("enum")
        if enum_values:
            enum_name = f"{prop_name.capitalize()}Enum"
            linkml["enums"][enum_name] = {"permissible_values": {str(v): {} for v in enum_values}}
            return enum_name
        return None

    def process_properties(props, class_name):
        slots_list = []
        for prop_name, details in props.items():
            if prop_name.startswith("@"): continue
            full_slot_name = f"{class_name.lower()}_{prop_name}" if prop_name in ["name", "description",
                                                                                  "title"] else prop_name
            slots_list.append(full_slot_name)
            slot_def = {"description": details.get("description", "No description provided.")}

            if prop_name in OEP_MAPPING:
                slot_def["slot_uri"] = OEP_MAPPING[prop_name]
            else:
                slot_def["slot_uri"] = f"oep:{prop_name}"

            enum_range = extract_enum(prop_name, details)
            if enum_range: slot_def["range"] = enum_range

            prop_type = details.get("type")
            if prop_type == "array":
                slot_def["multivalued"] = True
                items = details.get("items", {})
                if items.get("type") == "object":
                    range_name = prop_name.capitalize().rstrip('s')
                    if prop_name == "isAbout": range_name = "Isabout"
                    slot_def["range"] = range_name
                    process_properties(items.get("properties", {}), range_name)
            elif prop_type == "object":
                range_name = prop_name.capitalize()
                slot_def["range"] = range_name
                process_properties(details.get("properties", {}), range_name)

            linkml["slots"][full_slot_name] = slot_def
        linkml["classes"][class_name] = {"slots": slots_list}

    process_properties(jsonschema.get("properties", {}), "Dataset")
    linkml["classes"]["Dataset"]["tree_root"] = True

    # 1. Save YAML
    os.makedirs(os.path.dirname(OUTPUT_YAML), exist_ok=True)
    with open(OUTPUT_YAML, "w") as f:
        yaml.dump(linkml, f, sort_keys=False, allow_unicode=True)
    print(f"YAML generated at: {OUTPUT_YAML}")

    # 2. Generate the Vocabulary (RDF Schema in JSON-LD)
    generate_vocabulary(OUTPUT_YAML, OUTPUT_VOCAB)


if __name__ == "__main__":
    bootstrap()
