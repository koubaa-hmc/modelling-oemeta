import yaml
import requests

SCHEMA_URL = "https://raw.githubusercontent.com/OpenEnergyPlatform/oemetadata/production/oemetadata/v2/v20/schema.json"
OUTPUT_PATH = "src/oemeta_schema/schema/oemetadata.yaml"

OEO_MAPPING = {
    "title": "schema:name",
    "description": "schema:description",
    "license": "schema:license",
    "subject": "oeo:OEO_00010000",
    "spatial": "schema:spatialCoverage",
    "temporal": "schema:temporalCoverage",
    "sector": "oeo:OEO_00000356",
    "unit": "oeo:OEO_00010045",
    "path": "schema:contentUrl",
    "format": "schema:encodingFormat"
}


def bootstrap():
    jsonschema = requests.get(SCHEMA_URL).json()

    linkml = {
        "id": "https://openenergyplatform.org/metadata/v20",
        "name": "oemetadata_v20",
        "prefixes": {
            "linkml": "https://w3id.org/linkml/",
            "schema": "http://schema.org/",
            "oeo": "http://openenergyontology.org/ontology/",
            "oep": "https://openenergyplatform.org/metadata/v20/"
        },
        "default_prefix": "oep",
        "default_range": "string",
        "classes": {},
        "slots": {}
    }

    def process_properties(props, class_name):
        slots_list = []
        for prop_name, details in props.items():
            # Create a unique slot name to avoid collisions across classes
            # e.g., resource_name vs dataset_name
            full_slot_name = f"{class_name.lower()}_{prop_name}" if prop_name in ["name", "description"] else prop_name
            slots_list.append(full_slot_name)

            slot_def = {"description": details.get("description", "")}
            if prop_name in OEO_MAPPING:
                slot_def["slot_uri"] = OEO_MAPPING[prop_name]

            # Handle Nested Arrays (like 'resources')
            if details.get("type") == "array":
                slot_def["multivalued"] = True
                items = details.get("items", {})
                if items.get("type") == "object":
                    range_name = prop_name.capitalize().rstrip('s')
                    slot_def["range"] = range_name
                    process_properties(items.get("properties", {}), range_name)

            # Handle Nested Objects (like 'schema')
            elif details.get("type") == "object":
                range_name = prop_name.capitalize()
                slot_def["range"] = range_name
                process_properties(details.get("properties", {}), range_name)

            linkml["slots"][full_slot_name] = slot_def

        linkml["classes"][class_name] = {"slots": slots_list}

    process_properties(jsonschema.get("properties", {}), "Dataset")
    linkml["classes"]["Dataset"]["tree_root"] = True

    with open(OUTPUT_PATH, "w") as f:
        yaml.dump(linkml, f, sort_keys=False, allow_unicode=True)

    print(f"Deep-mapped YAML generated at: {OUTPUT_PATH}")


if __name__ == "__main__":
    bootstrap()
