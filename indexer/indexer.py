import json
import logging
import time
import urllib2
import urllib
import urlparse

import config

def has_resumption_token(data):
    return data.has_key("resumption_token") and \
        data['resumption_token'] is not None and \
        data['resumption_token'] != "null"

def next_url(lr_url, data):
    logging.info("resumption_token: " + data['resumption_token'])
    url_parts = urlparse.urlparse(lr_url)
    new_query = urllib.urlencode({"resumption_token":data['resumption_token']})
    return urlparse.urlunparse((url_parts[0],
                                url_parts[1],
                                url_parts[2],
                                url_parts[3],
                                new_query,
                                url_parts[5]))

def fetch_records(lr_url):
    while True:
        try:
            response = urllib2.urlopen(lr_url)
            break
        except Exception, e:
            logging.error("Failed to fetch: %s" % lr_url)
            time.sleep(config.config['lr-error-sleep'])
    return json.load(response)
