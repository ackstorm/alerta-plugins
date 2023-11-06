import os
import logging

from flask import current_app
from alerta.plugins import PluginBase
from alerta.models.enums import Status

LOG = logging.getLogger('alerta.plugins.mimiralert')
TAGS_TO_ATTRIBUTES = ['timeperiod', 'env', 'cluster', 'peer_id', 'tenant_id']


class MimirAlert(PluginBase):
    def __init__(self, name=None):
        super().__init__(name)

    def _parse_alert(self, alert):
        # Tags to attributes and build _tags
        _tags = {}
        for item in alert.tags:
            try:
                k, v = item.split('=', 1)
                _tags[k] = v
                if k in TAGS_TO_ATTRIBUTES and not alert.attributes.get(k):
                    alert.attributes[k] = v
            except ValueError:
                pass

        # Exclude non multi-peer events (not comming from mimir)
        if not _tags.get('peer_id'):
            return alert    

        LOG.info("Processing mimir alert: %s", alert.id)         

        # Hardcoded timeout
        alert.timeout = 600
        if alert.event == 'Watchdog':
            alert.severity = 'critical'

        # Always define a service
        if not alert.service or not alert.service[0]:
            alert.service = [_tags.get('namespace')] if _tags.get('namespace') else ['global']

        # Set environment and timeperiod
        alert.environment = _tags.get('env', current_app.config['DEFAULT_ENVIRONMENT'])
        alert.environment = 'prod' if alert.environment in ['pro', 'prd'] else alert.environment # fix 3char paranoid envs
        alert.attributes['timeperiod'] = '24x7' if alert.environment == 'prod' else '8x5'

        # Set base propperties
        alert.origin = 'prometheus/' + _tags['peer_id']
        alert.attributes['peer_id'] = _tags['peer_id'] # different heartbeats per peer

        # Genrate unique descriptive resource
        alert.resource = '{}/{}/{}/{}'.format(
            alert.environment,
            alert.origin,
            alert.event,
            alert.service[0]
        )

        # Enhance resource
        if alert.event == 'KubeHpaMaxedOut' and _tags.get('horizontalpodautoscaler'):
            alert.resource += '/hpa={}'.format(_tags['horizontalpodautoscaler'])

        elif _tags.get('container') and _tags.get('container') != "kube-rbac-proxy-main":
            alert.resource += '/container={}'.format(_tags['container'])

        elif _tags.get('app'):
            alert.resource += '/app={}'.format(_tags['app'])

        elif _tags.get('name'):
            alert.resource += '/name={}'.format(_tags['name'])    
        
        elif _tags.get('job'):
            alert.resource += '/job={}'.format(_tags['job'])    

        elif _tags.get('deployment'):
            alert.resource += '/deploy={}'.format(_tags['deployment'])    

        elif _tags.get('group'):
            alert.resource += '/{}'.format(_tags['group'])

        return alert

    def pre_receive(self, alert, **kwargs):
        if alert.event_type == "prometheusAlert":
            alert = self._parse_alert(alert)
        return alert

    def post_receive(self, alert):
        return

    def status_change(self, alert, status, text):
        return
