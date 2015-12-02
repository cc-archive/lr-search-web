import urlparse
from elasticsearch import Elasticsearch

import config

es = Elasticsearch(hosts=config.config['es-nodes'])

def parse_license_elements(lic):
    """Return an empty list if invalid,
       or a list of path components, but with any deed or legalcode
       at the end stripped (e.g. deed, legalcode, legalcoda.ca, deed.it)
       e.g. ['licenses', 'by-sa', '2.0', 'es']
       or e.g. ['licenses', 'by-sa', '2.0']
       or e.g. ['licenses', 'by-sa', '4.0']
       or e.g. ['publicdomain', 'zero', '1.0']
       or e.g. ['publicdomain', 'mark', '1.0']"""
    #TODO: If this will ever be called more than once, cache the results
    components = urlparse.urlparse(lic)
    # If it's e.g. 'copyright' then just return an empty list
    if components.scheme:
        elements = [c for c in components.path.split('/')
                    if not c == ''
                    and not c.startswith('deed')
                    and not c.startswith('legalcode')]
    else:
        elements = []
    return elements

def store_entity(envelope, title, description, lic, levels):
    body = {'doc_ID':envelope['doc_ID'],
            'resource_locator':envelope['resource_locator'],
            'resource_data':envelope['resource_data'],
            'title':title,
            'description':description,
            'license':lic,
            'levels':levels}
    license_elements = parse_license_elements(lic)
    # This will be publicdomain or license. Forgive the naming.
    body['license_category'] = license_elements[0]
    license_name = license_elements[1]
    license_modules = license_name.split('-')
    body['license_name'] = license_name
    body['license_modules'] = license_modules
    body['license_version'] = license_elements[2]
    if len(license_elements) > 3:
        body['license_jurisdiction'] = license_elements[3]
    es.index(index=config.config['es-index'],
             doc_type=config.config['es-index-type'],
             id=envelope['doc_ID'],
             body=body)
