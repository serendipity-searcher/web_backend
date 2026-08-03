# SPARQL queries for the v2 API schema, mirroring extraction_sparql.py (v1).
#
# Schema changes vs. v1 that shaped these queries:
#   - Records use a compact @context (crm/owl/xsd/prov/rdfs) instead of full URIs.
#   - The object's own @id is already the stable URI (no more isVersionOf/timestamped
#     snapshot pattern) -> object_URI = ?o directly.
#   - Title lives directly on the object as rdfs:label (v1: crm:P102_has_title).
#   - Description moved to crm:P67i_is_referred_to_by -> crm:E33_Linguistic_Object,
#     identified by crm:P2_has_type label "description" (v1: crm:P3_has_note).
#   - Object classification is crm:P2_has_type directly on the object
#     (v1: crm:P41i_was_classified_by -> crm:P42_assigned -> concept).
#   - Subcollection moved from crm:P46i_forms_part_of to crm:P106i_forms_part_of
#     (crm:P46i_forms_part_of in v2 now means something different: an object being
#     part of another whole object). There's no separate subcollection "type" field
#     anymore, only crm:E78_Curated_Holding + rdfs:label.
#   - Materials/parts drop the crm:P2_has_type indirection: crm:P45_consists_of
#     points straight at the crm:E57_Material node with its own rdfs:label.
#     Parts: crm:P46_is_composed_of -> crm:P46_has_component, part label is
#     directly on the component node (rdfs:label) instead of via crm:P3_has_note.
#   - Place/maker are linked directly (crm:P7_took_place_at / crm:P14_carried_out_by)
#     instead of through the la:equivalent indirection used in v1.
#   - "Coining"/conception (v1: crm:P67i_is_referred_to_by -> crm:P94i_was_created_by,
#     nested) is now a top-level crm:P94i_was_created_by directly on the object.
#     NOTE: in the current v2 dump this event has no crm:P4_has_time-span and its
#     place/agent are (almost) always identical to crm:P108i_was_produced_by, i.e.
#     it looks like a duplicate of the production event rather than a distinct
#     coining/conception event. The query is kept analogous to v1 in case this
#     gets populated with genuinely distinct data later.
#   - Acquisition time-span sits directly on crm:P24i_changed_ownership_through
#     (v1 required drilling into crm:P32_used_general_technique first).


prefixes = """
PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
PREFIX owl: <https://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

core_query = prefixes + """

SELECT
    ?object_number
    (?o AS ?object_URI)
    ?title
    ?description
    ?objectname_URI ?objectname_label

    ?subcollection_URI ?subcollection_name

    ### materials

    ?material_URI ?material_label
    ?part_label ?part_material_URI ?part_material_label

WHERE {
    ?o crm:P1_is_identified_by ?idNode .
    ?idNode a crm:E42_Identifier ;
            rdfs:label ?object_number ;
            crm:P2_has_type [ rdfs:label "Objectnummer" ] . # primary ID

    OPTIONAL { ?o rdfs:label ?title . }

    OPTIONAL {
        ?o crm:P67i_is_referred_to_by ?descNode .
        ?descNode crm:P2_has_type [ rdfs:label "description" ] ;
                  rdfs:label ?description .
    }

    OPTIONAL {
        ?o crm:P2_has_type ?objectname_URI .
        ?objectname_URI rdfs:label ?objectname_label .
    }

    OPTIONAL {
        ?o crm:P106i_forms_part_of ?subcollection_URI .
        OPTIONAL { ?subcollection_URI rdfs:label ?subcollection_name . }
    }

    ### materials

    OPTIONAL {
        ?o crm:P45_consists_of ?material_URI .
        ?material_URI rdfs:label ?material_label .
    }

    OPTIONAL {
        ?o crm:P46_has_component ?compNode .
        ?compNode rdfs:label ?part_label .
        OPTIONAL {
            ?compNode crm:P45_consists_of ?part_material_URI .
            ?part_material_URI rdfs:label ?part_material_label .
        }
    }
}
"""


creation_prov_query = prefixes + """

SELECT
    ?object_number
    ?creation_time
    ?creation_place_URI ?creation_place_label
    ?maker_URI ?maker_label
    ?technique_URI ?technique_label

WHERE {

    ?o crm:P1_is_identified_by [ a crm:E42_Identifier ; rdfs:label ?object_number ;
                                  crm:P2_has_type [ rdfs:label "Objectnummer" ] ] . # primary ID

    ?o crm:P108i_was_produced_by ?prodEv .
    OPTIONAL { ?prodEv crm:P4_has_time-span [ rdfs:label ?creation_time ] . }
    OPTIONAL { ?prodEv crm:P7_took_place_at ?creation_place_URI . ?creation_place_URI rdfs:label ?creation_place_label . }
    OPTIONAL { ?prodEv crm:P14_carried_out_by ?maker_URI . ?maker_URI rdfs:label ?maker_label . }
    OPTIONAL { ?prodEv crm:P32_used_general_technique ?technique_URI . ?technique_URI rdfs:label ?technique_label . }

}
"""


# NOTE: see header comment - in the current v2 data this is effectively a
# duplicate of the production event above (same place/agent, no time-span).
coining_prov_query = prefixes + """

SELECT
    ?object_number
    ?coin_time
    ?coin_place_URI ?coin_place_label
    ?coiner_URI ?coiner_label

WHERE {

    ?o crm:P1_is_identified_by [ a crm:E42_Identifier ; rdfs:label ?object_number ;
                                  crm:P2_has_type [ rdfs:label "Objectnummer" ] ] . # primary ID

    ?o crm:P94i_was_created_by ?coinEv .
    OPTIONAL { ?coinEv crm:P4_has_time-span [ rdfs:label ?coin_time ] . }
    OPTIONAL { ?coinEv crm:P7_took_place_at ?coin_place_URI . ?coin_place_URI rdfs:label ?coin_place_label . }
    OPTIONAL { ?coinEv crm:P14_carried_out_by ?coiner_URI . ?coiner_URI rdfs:label ?coiner_label . }
}
"""


acquisition_query = prefixes + """

SELECT DISTINCT
    ?object_number
    ?acquisition_time
WHERE {
    ?o crm:P1_is_identified_by [ a crm:E42_Identifier ; rdfs:label ?object_number ;
                                  crm:P2_has_type [ rdfs:label "Objectnummer" ] ] . # primary ID

    ?o crm:P24i_changed_ownership_through [ crm:P4_has_time-span [ rdfs:label ?acquisition_time ] ] .
}
"""
