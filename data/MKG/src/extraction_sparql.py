ns = dict(lido="http://www.lido-schema.org",
         oai="http://www.openarchives.org/OAI/2.0/")

def get_value(tree, xpath_expr, keep_iterable=True):
    finds =  tree.xpath(xpath_expr, namespaces=ns)
    if len(finds) < 1: 
        # print(f"{xpath_expr=} not found!")
        return "" if not keep_iterable else ("",)
    elif len(finds) == 1: return finds[0].text if not keep_iterable else (finds[0].text,)
    else: return tuple(set(el.text for el in finds))

def website_link(tree):
    xp = 'lido:lido//lido:recordInfoLink'
    return get_value(tree, xp)
    


def record_id(tree):
    xp = 'lido:lido/lido:lidoRecID'
    return get_value(tree, xp)


def inv_number(tree):
    xp = 'lido:lido//lido:repositorySet/lido:workID[@lido:type="Inventarnummer"]'
    return get_value(tree, xp)

def title(tree):
    xp = 'lido:lido//lido:titleWrap/lido:titleSet/lido:appellationValue[@lido:pref="preferred"]'
    return get_value(tree, xp)


# Beschreibung Veröffentlichung
def description(tree):
    xp = 'lido:lido//lido:objectDescriptionWrap/lido:objectDescriptionSet[@lido:type="Beschreibung"]/lido:descriptiveNoteValue'
    return get_value(tree, xp)


def collection(tree):
    xp = 'lido:lido//lido:classification[@lido:type="Sammlung"]/lido:term'
    return get_value(tree, xp)

def objectname(tree):
    # xp = '''//lido:lido//lido:objectWorkType[@lido:type="Objektbezeichnung"]/lido:term'''
    # "the string "Objectbezeichnung" doesn't occur in any of the record pages
    xp = '''lido:lido//lido:objectDescriptionSet[@lido:type="weitere Objektbezeichnung"]/lido:descriptiveNoteValue'''
    return get_value(tree, xp)


def objecttype(tree):
    xp = 'lido:lido//lido:classification[@lido:type="Sachgruppe"]/lido:term[@lido:pref="preferred"]'
    # xp2 = '//lido:lido//lido:objectDescriptionWrap/lido:objectDescriptionSet[@lido:type="weitere Objektbezeichnung"]/lido:descriptiveNoteValue'
    
    # xp3 = 'ldo:lido//lido:objectWorkType[@lido:type="Objektbezeichnung"]/lido:term'
    # obj_type2 = get_value(tree, xp2)
    # if obj_type2:
    #     if isinstance(obj_type2, str):
    #         return obj_type2
    #     return (get_value(tree, xp),) + get_value(tree, xp2) 
    return get_value(tree, xp)


def material(tree):
    xp = 'lido:lido//lido:classification[@lido:type="Material"]/lido:term[@lido:pref="preferred"]'
    return get_value(tree, xp)

def technique(tree):
    xp = 'lido:lido//lido:classification[@lido:type="Technik"]/lido:term[@lido:pref="preferred"]'
    return get_value(tree, xp)  

def artstyle(tree):
    xp = 'lido:lido//lido:classification[@lido:type="Stil"]/lido:term[@lido:pref="preferred"]'
    return get_value(tree, xp)


def subject(tree):
    xp = 'lido:lido//lido:subject[@lido:type="Ikonographie"]/lido:subjectConcept/lido:term[@lido:pref="preferred"]'
    return get_value(tree, xp)

# WARNING: xml:lang is sometimes also lido:lang
# evnt types:
# Auftrag, Ausstellung, Bearbeitung, Ereignis, Erweiterung, Fund, Gebrauch, geistige Schoepfung, Planung
# Veroeffentlichung, Vertrieb, Vollendung, Zerstoerung
def prov(tree):
    make_event = """lido:lido//lido:eventSet/lido:event[
                    lido:eventType/lido:term="Entwurf" or
                    lido:eventType/lido:term="Herstellung" or
                    lido:eventType/lido:term="Ausführung"
                ]"""
    xp_maker = f'{make_event}//lido:nameActorSet/lido:appellationValue[@lido:pref="preferred"]'
    xp_maker_role = f'{make_event}//lido:roleActor/lido:term[@lido:pref="preferred"]'
    xp_date1 = f'{make_event}/lido:eventDate/lido:date/lido:earliestDate'
    xp_date2 = f'{make_event}/lido:eventDate/lido:date/lido:latestDate'
    xp_displaydate = f'{make_event}/lido:eventDate/lido:displayDate'
    xp_place = f"""{make_event}/lido:eventPlace/lido:place/lido:namePlaceSet/lido:appellationValue[
                                                                                @lido:pref="preferred" and 
                                                                                (@xml:lang="de" or @lido:lang="de")]"""

    return dict(
        maker = get_value(tree, xp_maker),
        maker_role = get_value(tree, xp_maker_role),
        date_begin = get_value(tree, xp_date1),
        date_end = get_value(tree, xp_date2),
        place = get_value(tree, xp_place)
    )

def creditline(tree):
    xp = 'lido:lido//lido:rightsWorkSet/lido:creditLine'
    return get_value(tree, xp)

def recordrights(tree):
    xp = 'lido:lido//lido:recordWrap/lido:recordRights/lido:rightsType/lido:term'
    return get_value(tree, xp)

def first_image(tree, thumbnail=False):
    version = "image_thumbnail" if thumbnail else "image_master"
    xp = f'lido:lido//lido:resourceWrap/lido:resourceSet[@lido:sortorder="1"]/lido:resourceRepresentation[@lido:type="{version}"]/lido:linkResource'
    return get_value(tree, xp)

def first_image_rights(tree, thumbnail=False):
    xp = f'lido:lido//lido:resourceWrap/lido:resourceSet[@lido:sortorder="1"]/lido:rightsResource//lido:term'
    return get_value(tree, xp)


def related_works(tree):
    xp_rel_type = "lido:lido//lido:relatedWorkSet/lido:relatedWorkRelType/lido:term"
    xp_rel_obj = "lido:lido//lido:relatedWorkSet/lido:relatedWork/lido:object/lido:objectID"
    types, ids = get_value(tree, xp_rel_type, keep_iterable=True), get_value(tree, xp_rel_obj, keep_iterable=True)
    if not types: return None
    return tuple(zip(types, ids))

def build_record(tree):
    rec = dict(
        object_number = inv_number(tree),
        record_id = record_id(tree),

        
        title = title(tree),
        description = description(tree),

        collection = collection(tree),
        objectname = objectname(tree),
        objecttype = objecttype(tree),
        material = material(tree),
        technique = technique(tree),
        artstyle = artstyle(tree),
        subject = subject(tree),
        
        creditline = creditline(tree),
        recordrights = recordrights(tree),

        img_url = first_image(tree),
        thumb_url = first_image(tree, thumbnail=True),
        img_rights = first_image_rights(tree),

        # MISSING ALMOST EVERYWHERE
        # related_works = related_works(tree)
    )
    rec = rec | prov(tree)
    return rec


def from_records(tree):
    for rec_t in t.xpath("//oai:record/oai:metadata", namespaces=ns):
        yield build_record(rec_t)


def list_namespace_info():
    import requests as r
    return r.get("http://d-nb.info/gnd/4568024-3/about/lds").text
