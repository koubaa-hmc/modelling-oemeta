import json
from rdflib import Graph, RDF, RDFS, Namespace, URIRef

# Define Namespaces
OEP = Namespace("https://openenergyplatform.org/metadata/v20/")
LINKML = Namespace("https://w3id.org/linkml/")
OWL = Namespace("http://www.w3.org/2002/07/owl#")


def purify_vocabulary(input_path, output_path):
    print(f"Purifying and re-typing vocabulary: {input_path}...")

    # 1. Load the existing graph
    g = Graph()
    g.parse(input_path, format="json-ld")

    # 2. Create a new graph for the clean data
    clean_g = Graph()

    # Bind prefixes for the output
    clean_g.bind("oep", OEP)
    clean_g.bind("rdfs", RDFS)
    clean_g.bind("rdf", RDF)
    clean_g.bind("owl", OWL)
    clean_g.bind("skos", Namespace("http://www.w3.org/2004/02/skos/core#"))

    # Define the Type Mapping
    # Any subject with these types will be re-assigned to the target type
    PROPERTY_TYPES = {LINKML.SlotDefinition, OWL.ObjectProperty, OWL.DatatypeProperty, RDF.Property}
    CLASS_TYPES = {LINKML.ClassDefinition, OWL.Class, RDFS.Class}

    # 3. Process the graph
    processed_subjects = set()

    for s in g.subjects(unique=True):
        # Determine the "Pure" type
        new_type = None
        current_types = set(g.objects(s, RDF.type))

        if current_types.intersection(PROPERTY_TYPES):
            new_type = RDF.Property
        elif current_types.intersection(CLASS_TYPES):
            new_type = RDFS.Class

        # If it's a Property or Class, migrate all its non-type attributes
        if new_type:
            clean_g.add((s, RDF.type, new_type))
            for p, o in g.predicate_objects(s):
                # Skip the original type declarations and LinkML-specific internal metadata
                if p == RDF.type or "linkml" in str(p).lower():
                    continue
                clean_g.add((s, p, o))
            processed_subjects.add(s)

    # 4. Final Serialization
    context = {
        "oep": str(OEP),
        "rdfs": str(RDFS),
        "rdf": str(RDF),
        "owl": str(OWL),
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "dct": "http://purl.org/dc/terms/"
    }

    # Serialize to dict
    raw_jsonld = json.loads(clean_g.serialize(format='json-ld', context=context))

    # Ensure @graph structure
    if isinstance(raw_jsonld, list):
        final_output = {"@context": context, "@graph": raw_jsonld}
    else:
        # If already an object, ensure it has the context and graph
        graph_content = raw_jsonld.get("@graph", raw_jsonld)
        final_output = {"@context": context, "@graph": graph_content}

    with open(output_path, "w") as f:
        json.dump(final_output, f, indent=4)

    print(f"Purification complete. Generated oep: Classes and Properties.")
    print(f"Saved to: {output_path}")


if __name__ == "__main__":
    purify_vocabulary("src/oemeta_schema/schema/oemetadata_vocabulary.jsonld",
                      "src/oemeta_schema/schema/oemetadata_vocabulary_pure.jsonld")
