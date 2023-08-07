import os
import logging

from flask import current_app
from alerta.plugins import PluginBase

LOG = logging.getLogger('alerta.plugins.ackstorm')
TAGS_TO_ATTRIBUTES = ['timeperiod', 'env', 'cluster', 'tenant_id']


class PrometheusParser(PluginBase):
    def __init__(self, name=None):
        super().__init__(name)

    def _parse_prometheus(self, alert):
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

        # Exclude non multi-tenant events
        if not _tags.get('tenant_id'):
            return alert             

        # ACKSTORM: Custom severity
        # Change severity for prometheus alerts, as defined in prometheus severity guidelines:
        # Critical: An issue, that needs to page a person to take instant action
        # Warning: An issue, that needs to be worked on but in the regular work queue or for during office hours rather than paging the oncall
        # Info: Is meant to support a trouble shooting process by informing about a non-normal situation for one or more systems but not worth a page or ticket on its own.

        alert.severity = 'critical' if alert.severity in ['page', 'email'] else alert.severity
        alert.severity = 'major'    if alert.severity in ['warning'] else alert.severity
        alert.severity = 'warning'  if alert.severity in ['info'] else alert.severity
        alert.severity = 'info'     if alert.severity in ['minor'] else alert.severity

        # Noise reduction
        if alert.event in ["KubeCPUOvercommit", "KubernetesVolumeFullInFourDays", "ThanosQueryGrpcClientErrorRate"]:
            alert.severity = 'warning'

        # Hardcoded timeouts (10m for watchdog or 380 for alerts)
        alert.timeout = 600 if alert.event == 'Watchdog' else 380 # repeat_interval: 2m configured in alertmanager

        # Always define a service
        alert.service = _tags.get('namespace') if _tags.get('namespace') else 'global'

        # Set environment and timeperiod
        alert.environment = _tags.get('env', current_app.config['DEFAULT_ENVIRONMENT'])
        alert.environment = 'prod' if alert.environment in ['pro', 'prd'] else alert.environment

        # Set base propperties
        alert.origin = 'prometheus/' + _tags['tenant_id']
        alert.attributes['tenant_id'] = _tags['tenant_id'] # different heartbeats per tenant

        # Genrate unique descriptive resource
        alert.resource = '{}/{}/{}/{}'.format(
            alert.environment,
            alert.origin,
            _tags.get('namespace') if _tags.get('namespace') else 'global',
            alert.event,
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
            LOG.info("Adapting prometheus webhook: %s %s", alert.id, alert.resource)
            alert = self._parse_prometheus(alert)
        
        return alert

    def post_receive(self, alert):
        return

    def status_change(self, alert, status, text):
        return
