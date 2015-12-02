from elasticsearch import Elasticsearch

import config

es = Elasticsearch(hosts=config.config['es-nodes'])

def create_schema():
    body = {
        'mappings': {
            config.config['es-index-type']: {
                '_source': {'enabled': True},
                # These are searched against atomically
                # so we do not want them analyzed.
                'properties': {
                    'levels': {'type':'string', 'index':'not_analyzed'},
                    'license': {'type':'string', 'index':'not_analyzed'},
                    'license_name': {'type':'string', 'index':'not_analyzed'},
                    'license_modules': {'type':'string', 'index':'not_analyzed'},
                    'license_version': {'type':'string', 'index':'not_analyzed'},
                    'license_jurisdiction': {'type':'string',
                                             'index':'not_analyzed'}
                }
            }
        }
    }
    es.indices.create(index=config.config['es-index'], body=body)
