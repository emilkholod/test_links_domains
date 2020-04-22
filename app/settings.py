import os

DOMAINS_KEY_IN_REDIS = os.getenv('DOMAIN_KEY_IN_REDIS', 'domains')
DOMAINS_KEY_LIST_IN_REDIS = os.getenv('DOMAIN_KEY_LIST_IN_REDIS', 'domains_list')
REDIS_HOST=os.getenv('REDIS_HOST', 'localhost')
