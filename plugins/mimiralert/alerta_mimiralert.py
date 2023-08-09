import os
import logging

from flask import current_app
from alerta.plugins import PluginBase

LOG = logging.getLogger('alerta.plugins.ackstorm')
TAGS_TO_ATTRIBUTES = ['timeperiod', 'env', 'cluster', 'tenant_id']
WARNING_ALERTS=[
    "KubeCPUOvercommit",
    "KubernetesVolumeFullInFourDays",
    "ThanosQueryGrpcClientErrorRate",
    "NodeNetworkInterfaceFlapping",
    "KubeAggregatedAPIErrors"
    ]


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

        # Exclude non multi-tenant events (not comming from mimir)
        if not _tags.get('tenant_id'):
            return alert    

        LOG.info("Processing mimir alert: %s", alert.id)         

        # Noise reduction
        if alert.event in WARNING_ALERTS:
            alert.severity = 'warning'

        # Hardcoded timeouts (10m for watchdog or 380 for alerts)
        alert.timeout = 600 if alert.event == 'Watchdog' else 380 # repeat_interval: 2m configured in alertmanager

        # Always define a service
        if not alert.service or not alert.service[0]:
            alert.service = [_tags.get('namespace')] if _tags.get('namespace') else ['global']
        else:
            LOG.info("Service is: '%s'", alert.service)  

        # Set environment and timeperiod
        alert.environment = _tags.get('env', current_app.config['DEFAULT_ENVIRONMENT'])
        alert.environment = 'prod' if alert.environment in ['pro', 'prd'] else alert.environment # fix 3char envs
        alert.attributes['timeperiod'] = '24x7' if alert.environment == 'prod' else '8x5'

        # Set base propperties
        alert.origin = 'prometheus/' + _tags['tenant_id']
        alert.attributes['tenant_id'] = _tags['tenant_id'] # different heartbeats per tenant

        # Genrate unique descriptive resource
        alert.resource = '{}/{}/{}/{}'.format(
            alert.environment,
            alert.origin,
            alert.event,
            alert.service[0]
        )

        # Enhance resource
        if alert.event == 'KubeHpaMaxedOut' and _tags.get('horizontalpodautoscaler'):
            alert.resource += '/{}'.format(_tags['horizontalpodautoscaler'])

        elif _tags.get('container'):
            alert.resource += '/{}'.format(_tags['container'])

        elif _tags.get('name'):
            alert.resource += '/{}'.format(_tags['name'])    
        
        elif _tags.get('job'):
            alert.resource += '/{}'.format(_tags['job'])    

        return alert  

    def pre_receive(self, alert, **kwargs):
        if alert.event_type == "prometheusAlert":
            alert = self._parse_alert(alert)
        
        return alert

    def post_receive(self, alert):
        return

    def status_change(self, alert, status, text):
        return
