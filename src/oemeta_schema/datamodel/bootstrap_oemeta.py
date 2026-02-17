import yaml
import requests

SCHEMA_URL = "https://raw.githubusercontent.com/OpenEnergyPlatform/oemetadata/production/oemetadata/v2/v20/schema.json"
OUTPUT_PATH = "src/oemeta_schema/schema/oemetadata.yaml"

OEO_MAPPING = {
    "title": "schema:name",
    "description": "schema:description",
    "license": "schema:license",
    "subject": "oeo:OEO_00010000",
    "sector": "oeo:OEO_00000356",
    "unit": "oeo:OEO_00010045"
}


def bootstrap():
    response = requests.get(SCHEMA_URL)
    jsonschema = response.json()

    linkml = {
        "id": "https://openenergyplatform.org/metadata/v20",
        "name": "oemetadata_v20",
        # ADD THIS LINE:
        "imports": ["linkml:types"],
        "prefixes": {
            "linkml": "https://w3id.org/linkml/",
            "schema": "http://schema.org/",
            "oeo": "http://openenergyontology.org/ontology/",
            "oep": "https://openenergyplatform.org/metadata/v20/",
            # Added xsd prefix which is often needed for types
            "xsd": "http://www.w3.org/2001/XMLSchema#"
        },
        "default_prefix": "oep",
        "default_range": "string",
        "classes": {},
        "slots": {},
        "enums": {}
    }

    def extract_enum(prop_name, details):
        """Extracts enum values if present in the JSON schema."""
        enum_values = details.get("enum")

        # Sometimes enums are hidden inside 'items' for arrays
        if not enum_values and "items" in details:
            enum_values = details["items"].get("enum")

        if enum_values:
            enum_name = f"{prop_name.capitalize()}Enum"
            linkml["enums"][enum_name] = {
                "permissible_values": {str(v): {} for v in enum_values}
            }
            return enum_name
        return None

    def process_properties(props, class_name):
        slots_list = []
        for prop_name, details in props.items():
            # SKIP RESERVED KEYWORDS
            if prop_name.startswith("@"):
                continue
            full_slot_name = f"{class_name.lower()}_{prop_name}" if prop_name in ["name", "description"] else prop_name
            slots_list.append(full_slot_name)

            slot_def = {"description": details.get("description", "")}

            # 1. Check for Enums
            enum_range = extract_enum(prop_name, details)
            if enum_range:
                slot_def["range"] = enum_range

            # 2. Handle Mapping
            if prop_name in OEO_MAPPING:
                slot_def["slot_uri"] = OEO_MAPPING[prop_name]

            # 3. Handle Hierarchy
            if details.get("type") == "array":
                slot_def["multivalued"] = True
                items = details.get("items", {})
                if items.get("type") == "object":
                    range_name = prop_name.capitalize().rstrip('s')
                    slot_def["range"] = range_name
                    process_properties(items.get("properties", {}), range_name)
            elif details.get("type") == "object":
                range_name = prop_name.capitalize()
                slot_def["range"] = range_name
                process_properties(details.get("properties", {}), range_name)

            linkml["slots"][full_slot_name] = slot_def

        linkml["classes"][class_name] = {"slots": slots_list}

    # Start processing
    process_properties(jsonschema.get("properties", {}), "Dataset")
    linkml["classes"]["Dataset"]["tree_root"] = True

    with open(OUTPUT_PATH, "w") as f:
        yaml.dump(linkml, f, sort_keys=False, allow_unicode=True)

    print(f"Success! YAML with Enums generated at: {OUTPUT_PATH}")


if __name__ == "__main__":
    bootstrap()
