import os
import yaml

with open(os.getenv('KUBE_CONFIG_FILE'), 'r') as f:
    _conf = yaml.load(f)

_contexts = {c['name']: c['context'] for c in _conf['contexts']}

CLUSTER_NAME = _contexts[_conf['current-context']]['cluster']
