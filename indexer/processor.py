import json, logging, re

from bs4 import BeautifulSoup

import config
import store

#NOTE: checking for en? Also check for en-US etc, so check for startwith en.

try:
    from html import unescape  # python 3.4+
except ImportError:
    try:
        from html.parser import HTMLParser  # python 3.x (<3.4)
    except ImportError:
        from HTMLParser import HTMLParser  # python 2.x
    unescape = HTMLParser().unescape

################################################################################
# License url analysis
################################################################################

def valid_license(lic):
    """Valid if it's a cc url,
       not if it's another url (we can't check reliably)
       or e.g. 'copyright'"""
    return lic and ('creativecommons.org/' in lic)

################################################################################
# LRMI
################################################################################

def process_lrmi(resource_data):
    #FIXME: replace any [0] with smarter data handling
    #       We rely on failure here to get caught higher up so we can learn more
    #       about this data in the wild
    lic = desc = title = levels = False
    data = resource_data['resource_data_description']
    props = data['resource_data']['items'][0]['properties']
    title = props['name'][0]
    desc = props['description']
    lic = props['useRightsUrl']
    levels = []
    try:
        levels += [r['educationalRole'] for r in data['resource_data']['audience']]
    except IndexError, e:
        pass
    try:
        levels += [props['educationalAlignment'][0]['properties']['educationalFramework'][0]]
    except IndexError, e:
        pass
    #keys = data.get('keys')
    return (title, desc, lic, levels)

################################################################################
# NSDL
################################################################################

def nsdl_desc(soup):
    # This will evaluate to logical false, so it's OK to use as default
    desc = ''
    # Should be dc:description
    d = soup.find('description')
    if d:
        desc = d.string
    # Should be dc:subject
    subjects = ' '.join([s.string for s in soup.find_all('subject')])
    if subjects != '':
        desc = desc + ' ' + subjects
    return desc

def nsdl_title(soup):
    # Should be dc:title
    title = soup.find('title')
    if title:
        title = title.string
    return title

def nsdl_license(soup):
    # should be dc:rights, but bs4 doesn't handle namespaces properly
    lic = soup.find('rights', attrs={'xsi:type':'dct:URI'})
    if lic:
        lic = lic.string
    return lic

def nsdl_education_levels(soup):
    # should be dct:educationLevel
    return [l.string for l in soup.find_all('educationLevel')]

def process_nsdl_dc(resource_data):
    title = desc = lic = levels = False
    data = resource_data.get('resource_data', '')
    soup = BeautifulSoup(data, "xml")
    title = nsdl_title(soup)
    desc = nsdl_desc(soup)
    lic = nsdl_license(soup)
    levels = nsdl_education_levels(soup)
    return (title, desc, lic, levels)

################################################################################
# LOM
################################################################################

# BeautifulSoup 4 is case sensitive
LOM_LICENSE = re.compile('[Ll]icense')
LOM_X_T_CC_ATTRS = {'rdf:resource':re.compile('creativecommons\.org')}
LOM_COST_IS_FREE = False

# Is the value of the rights/cost field "yes"?

def lom_cost_value(description):
    value_is_yes = False
    cost = description.find('cost')
    if cost:
        value = description.find('value')
        if value:
            value_is_yes = (value.string.strip().lower() == 'yes')
    return value_is_yes

def lom_license(description):
    lic = description.find('string', attrs={'language':'x-t-cc-url'})
    if lic:
        lic = lic.string
    else:
        lic = description.find('string', attrs={'language':'lt'})
        if lic and 'creativecommons.org/' in lic.string:
            lic = lic.string
    if not lic:
        rdf = description.find('string', attrs={'language':'x-t-cc'})
        if rdf:
            try:
                dom = BeautifulSoup(unescape(rdf.string), "xml")
                lic_node = dom.find(LOM_LICENSE,
                                    attrs=LOM_X_T_CC_ATTRS)
                lic = lic_node.attrs.get('rdf:resource')
            except:
                # If the data upsets BeautifulSoup we want no part of it
                if rdf.string != 'Edu3':
                    logging.info(rdf.string)
                    logging.info('------------------------------------------------------------')
                pass
    return lic

def lom_desc(soup):
    #TODO: also taxon?
    # This will evaluate to logical false, so it's OK to use as default
    desc = ''
    general = soup.find('general')
    if general:
        d = general.find('description')
        if d:
            string = d.find('string')
            if string:
                desc = string.string
        keywords = ' '.join([k.find('string').string
                             for k in general.find_all('keyword')])
        desc += ' ' + keywords
    return desc

def lom_title(soup):
    title = soup.find('title')
    if title:
        #FIXME: get all language strings e.g. <string language="ca">
        title = title.find('string')
    if title:
        title = title.string
    return title

# Parse local levels, e.g:
# http://www.ukoln.ac.uk/metadata/education/ukel/
# Translate to some commonly agreed standard or flatten all to age ranges
# OR treat each jurisdiction's levels separately.

# TEMPORARY VERSIONS

def naive_age_to_level(ars):
    #FXIME: THIS IS A TERRIBLE, TERRIBLE HACK. REPLACE WITH TAXONOMY ANALYSIS
    #FIXME: FOR DEMONSTRATION PURPOSES ONLY.
    try:
        arsfrom = ars.split('-')[0]
        if arsfrom == 'U':
            level = 'Higher Education'
        else:
            nars = int(arsfrom)
            if nars < 5:
                level = 'Preschool'
            elif nars < 7:
                level = 'Elementary School'
            elif nars < 9:
                level = 'Upper Elementary'
            elif nars < 12:
                level = 'Middle School'
            elif nars < 18:
                level = 'High School'
            elif nars < 22:
                level = 'Higher Education'
            else:
                level = 'Undergraduate'
    except:
        level = False
    return level

def lom_levels(soup):
    levels = []
    ar = soup.find('typicalAgeRange')
    if ar:
        ars = ar.find('string').string
        # Store for later better processing, and store current lookup
        level = naive_age_to_level(ars)
        if level:
            levels = ['typicalAgeRange:' + ars, level]
    return levels

def process_lom(resource_data):
    lic = desc = title = levels = False
    data = resource_data.get('resource_data', '')
    soup = BeautifulSoup(data, "xml")
    rights = soup.find('rights')
    if rights:
        description = rights.find('description')
        # We're only interested if there's likely to be license data
        if description:
            if LOM_COST_IS_FREE or not lom_cost_value(description):
                lic = lom_license(description)
    if lic:
        title = lom_title(soup)
    if title:
        desc = lom_desc(soup)
    if desc:
        levels = lom_levels(soup)
    return (title, desc, lic, levels)

################################################################################
# Processing resources
################################################################################

def process_resource_data(resource_data):
    kind = title = desc = lic = components = levels = False
    schemas = [schema.lower() for schema in resource_data.get('payload_schema', [])]
    try:
        if 'lom' in schemas:
            #logging.info("LOM")
            #logging.info(resource_data)
            #logging.info("---------------------------------------------------------")
            title, desc, lic, levels = process_lom(resource_data)
            kind = 'lom'
            pass
        elif 'nsdl_dc' in schemas:
            #logging.info("nsdl_dc")
            #logging.info(resource_data)
            #logging.info("---------------------------------------------------------")
            title, desc, lic, levels = process_nsdl_dc(resource_data)
            kind = 'nsdl_dc'
        elif 'lrmi' in schemas:
            logging.info("LRMI")
            logging.info(resource_data)
            logging.info("---------------------------------------------------------")
            title, desc, lic, levels = process_lrmi(resource_data)
            kind = 'lrmi'
        elif 'comm_para 1.0' in schemas:
            # Paradata doesn't tend to interest us (usage, stars etc.)
            if 'creativecommons.org/license' in resource_data['resource_data']:
                logging.info("comm_para")
                logging.info(resource_data)
                logging.info("---------------------------------------------------------")
            #lic, title = process_comm_para(resource_data)
            #kind = 'comm_para'
        if not (kind and title and desc and lic and levels):
            if 'creativecommons.org/license' in resource_data.get('resource_data', ''):
                logging.info("Failed to get all properties")
                logging.info(resource_data)
                logging.info("---------------------------------------------------------")
    except Exception as ex:
        logging.info(ex)
        import traceback
        logging.error(traceback.format_exc())
        logging.error("Resource Data Parsing Error")
        logging.error("---------------------------------------------------------")
    if not valid_license(lic):
        title = desc = lic = levels = False
    return (kind, title, desc, lic, levels)

def process_records(data):
    for record in data.get('listrecords', []):
        record_record = record.get('record')
        if record_record:
            resource_data = record_record.get('resource_data')
            if resource_data:
                #print resource_data['resource_data']
                kind, title, desc, lic, levels = process_resource_data(resource_data)
                if(title and desc and lic and levels):
                    logging.info("%s:%s\t%s\t%s\t%s" % (kind, title, desc, lic,
                                                        levels))
                    store.store_entity(resource_data, title, desc, lic, levels)
            else:
                logging.info(record)
                logging.info("---------------------------------------------------------")
        else:
            logging.info(record)
            logging.info("---------------------------------------------------------")

#if __name__ == '__main__':
#    source = json.load(open('test-data/1.json'))
#    process_records(source)
