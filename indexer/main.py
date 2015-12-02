import logging, time

import config, indexer, processor, schema

if __name__ == '__main__':
    logging.basicConfig(filename='results.log',
                        filemode='w',
                        level=logging.INFO)
    logging.info('Start')
    logging.info('Enforcing schema')
    schema.create_schema()
    logging.info('Enforced schema')
    lr_url = config.config['lr-node']
    delay = config.config['lr-sleep']
    while True:
        data = indexer.fetch_records(lr_url)
        processor.process_records(data)
        if indexer.has_resumption_token(data):
            lr_url = indexer.next_url(lr_url, data)
            #time.sleep(delay)
            #break
        else:
            print 'Done'
            break
