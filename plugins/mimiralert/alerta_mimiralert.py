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
        # Tags to attributes and build tags
        tags = {}
        for item in alert.tags:
            try:
                k, v = item.split('=', 1)
                tags[k] = v
                if k in TAGS_TO_ATTRIBUTES and not alert.attributes.get(k):
                    alert.attributes[k] = v
            except ValueError:
                pass

        # Exclude non multi-peer events (not comming from mimir)
        if not tags.get('peer_id'):
            return alert    

        LOG.info("Processing mimir alert: %s", alert.id)

        # Hardcoded timeout
        alert.timeout = 1800 # Alert timeout for non "send_resolved" from alertmanager
        if alert.event == 'Watchdog':
            alert.timeout = 900
            alert.severity = 'critical'

        # Exported namespace takes preference
        if tags.get('exported_namespace'):
            tags['namespace'] = tags['exported_namespace']

        # Always define a service
        if not alert.service or not alert.service[0]:
            alert.service = [tags.get('namespace')] if tags.get('namespace') else ['global']

        # Set environment and timeperiod
        alert.environment = tags.get('env', current_app.config['DEFAULT_ENVIRONMENT'])
        alert.environment = 'prod' if alert.environment in ['pro', 'prd'] else alert.environment # fix 3char paranoid envs
        if not alert.attributes.get('timeperiod'):
            alert.attributes['timeperiod'] = '24x7' if alert.environment == 'prod' else '12x5'

        # Set base propperties
        alert.origin = 'prometheus/' + tags['peer_id']
        alert.attributes['peer_id'] = tags['peer_id'] # different heartbeats per peer

        # Genrate unique descriptive resource
        alert.resource = '{}/{}/{}/{}'.format(
            alert.environment,
            alert.origin,
            alert.event,
            alert.service[0]
        )

        # Enhance resource
        if alert.event == 'KubeHpaMaxedOut' and tags.get('horizontalpodautoscaler'):
            alert.resource += '/hpa={}'.format(tags['horizontalpodautoscaler'])
        elif alert.event == 'BlackboxProbeFailed' and tags.get('ingress'):
            alert.resource += '/{}'.format(tags['ingress'])
        elif tags.get('deployment'):
            alert.resource += '/deployment={}'.format(tags['deployment'])
        elif tags.get('daemonset'):
            alert.resource += '/daemonset={}'.format(tags['daemonset'])
        elif tags.get('statefulset'):
            alert.resource += '/statefulset={}'.format(tags['statefulset'])
        elif tags.get('app'):
            alert.resource += '/app={}'.format(tags['app'])
        elif tags.get('name'):
            alert.resource += '/name={}'.format(tags['name'])    
        elif tags.get('job'):
            alert.resource += '/job={}'.format(tags['job'])    
        elif tags.get('job_name'):
            alert.resource += '/job={}'.format(tags['job_name'])    
        elif tags.get('group'):
            alert.resource += '/{}'.format(tags['group'])
        elif tags.get('container') and not tags.get('container').startswith("kube-rbac-proxy"):
            alert.resource += '/container={}'.format(tags['container'])

        return alert

    def pre_receive(self, alert, **kwargs):
        if alert.event_type == "prometheusAlert":
            alert = self._parse_alert(alert)
        return alert

    def post_receive(self, alert):
        return

    def status_change(self, alert, status, text):
        return
