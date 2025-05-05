# ### ID properties:  
#     http://www.w3.org/ns/adms#identifier -> holds the object number (main & unique ID)
#     http://xmlns.com/foaf/0.1/page
#     http://purl.org/dc/terms/isVersionOf -> the version ID for the event stream (allows modeling API generation-specific versions)

# ### constants:  
#     crm:P50_has_current_keeper (namely 'http://www.wikidata.org/entity/Q1809071' = DMG)
#     crm:P55_has_current_location (namely 'depot' to 97%)

# ### technical properties:  
#     http://www.w3.org/ns/prov#generatedAtTime (near-constant: almost all objects have value '2023-06-01'/'-02')
#     crm:P129iis_subject_of (-> this is the URI of the IIIF server)




# ### core meta info: 
#     crm:P102_has_title
#     crm:P3_has_note (-> this is the description) 
#     crm:P41i_was_classified_by (-> object name/kind of object)

#     crm:P46i_forms_part_of (-> this is a subcollection/theme)
#     http://purl.org/dc/terms/isPartOf (-> this seems to be for exhibitions)

    
# ### material properties
#     crm:P43_has_dimension => 96%
#     crm:P46_is_composed_of
#     crm:P45_consists_of

# ### prov(-like) properties

# => contain info such as creation time, place, technique & maker

#     crm:P108i_was_produced_by ->
#     crm:P67i_is_referred_to_by -> models event of conception (of type crm:Concept)
#     crm:P24i_changed_ownership_through => 100% 




prefixes = """
PREFIX crm: <http://www.cidoc-crm.org/cidoc-crm/>
PREFIX la:  <https://linked.art/ns/terms/>
PREFIX schema: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX purl: <http://purl.org/dc/terms/>
PREFIX w3: <http://www.w3.org/ns/adms#>
PREFIX cest: <https://www.projectcest.be/wiki/Publicatie:Invulboek_objecten/Veld/>
PREFIX eu: <http://data.europa.eu/m8g/>
"""

core_query = prefixes + """

SELECT 
    ?object_number
    ?object_URI
    ?title
    ?description
    ?objectname_URI ?objectname_label

    ?subcollection_URI ?subcollection_type ?subcollection_name

    ### materials
    
    ?material_URI ?material_label
    ?part_label ?part_material_URI ?part_material_label

WHERE {
    ?o purl:isVersionOf ?object_URI .
    ?o w3:identifier [ skos:notation ?object_number; crm:P2_has_type cest:Waarde_objectnummer ] . # primary ID

    OPTIONAL {?o crm:P102_has_title ?title .}
  
    OPTIONAL {?o crm:P3_has_note ?description .}

  
    OPTIONAL {?o crm:P41i_was_classified_by ?c .
            ?c crm:P42_assigned ?objectname_URI .
            ?objectname_URI skos:prefLabel ?objectname_label .}

  OPTIONAL {
      ?o crm:P46i_forms_part_of ?subcollection_URI .
      OPTIONAL { ?subcollection_URI crm:P2_has_type ?subcollection_type . } # only if ?x is a concept, others are nameless collections
      OPTIONAL { ?subcollection_URI crm:P3_has_note ?subcollection_name . } # only if ?x is a concept, others are nameless collections
    }
    
    ### materials
  
    OPTIONAL {?o crm:P45_consists_of ?m . 
            ?m crm:P2_has_type ?material_URI .
            ?material_URI skos:prefLabel ?material_label .}

    OPTIONAL {?o crm:P46_is_composed_of ?compNode .
            ?compNode crm:P45_consists_of [ crm:P2_has_type ?part_material_URI ] . ?part_material_URI skos:prefLabel ?part_material_label .
            ?compNode crm:P3_has_note ?part_label . }
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

    ?o w3:identifier [ skos:notation ?object_number; crm:P2_has_type cest:Waarde_objectnummer ] . # primary ID
    
    ?o crm:P108i_was_produced_by ?prodEv . 
    ?prodEv crm:P4_has_time-span ?creation_time . # not optional acc. to Gent's data model (and CIDOC CRM?) ## this is a primitive string (as opposed eu:startTime & eu:endTime, is that valid?) 
    OPTIONAL { ?prodEv crm:P7_took_place_at [ la:equivalent ?creation_place_URI ] . ?creation_place_URI skos:prefLabel ?creation_place_label . }
    OPTIONAL { ?prodEv crm:P14_carried_out_by [ la:equivalent ?maker_URI ] . ?maker_URI schema:label ?maker_label . }
    OPTIONAL { ?prodEv crm:P32_used_general_technique [ crm:P2_has_type ?technique_URI ] . ?technique_URI skos:prefLabel ?technique_label . }
    
}
"""


coining_prov_query = prefixes + """

SELECT 
    ?object_number
    ?coin_time 
    ?coin_place_URI ?coin_place_label 
    ?coiner_URI ?coiner_label 

WHERE {

    ?o w3:identifier [ skos:notation ?object_number; crm:P2_has_type cest:Waarde_objectnummer ] . # primary ID

    ?o crm:P67i_is_referred_to_by [ crm:P94i_was_created_by ?coinEv ] . 
    ?coinEv crm:P4_has_time-span ?coin_time .
    OPTIONAL { ?coinEv crm:P7_took_place_at [ la:equivalent ?coin_place_URI ] . ?coin_place_URI skos:prefLabel ?coin_place_label .}
    OPTIONAL { ?coinEv crm:P14_carried_out_by [ la:equivalent ?coiner_URI ] . ?coiner_URI schema:label ?coiner_label .}
}
"""

# acquisition_query = prefixes+"""
# SELECT
#     ?object_number
#     ?acq_time
# WHERE {
#     ?o w3:identifier [ skos:notation ?object_number; crm:P2_has_type cest:Waarde_objectnummer ] . # primary ID
#     # NOT NEEDED BECAUSE START == END ALWAYS # ?o crm:P24i_changed_ownership_through [crm:P32_used_general_technique [crm:P2_has_type cest:Term_verwervingsmethode] ; crm:P4_has_time-span [ eu:endTime ?end ; eu:startTime ?start] ] .
#     ?o crm:P24i_changed_ownership_through [crm:P32_used_general_technique [crm:P2_has_type cest:Term_verwervingsmethode] ; crm:P4_has_time-span [ eu:startTime ?acq_time ] ] .
# }
# """

acquisition_query = prefixes+"""

SELECT DISTINCT
    ?object_number
    ?acquisition_time
WHERE {
    ?o w3:identifier [ skos:notation ?object_number; crm:P2_has_type cest:Waarde_objectnummer ] . # primary ID

    # NOT NEEDED BECAUSE START == END ALWAYS # ?o crm:P24i_changed_ownership_through [crm:P32_used_general_technique [crm:P2_has_type cest:Term_verwervingsmethode] ; crm:P4_has_time-span [ eu:endTime ?end ; eu:startTime ?start] ] .
    ?o crm:P24i_changed_ownership_through [crm:P32_used_general_technique [crm:P2_has_type cest:Term_verwervingsmethode] ; crm:P4_has_time-span [ eu:startTime ?acquisition_time ] ] .
}
"""