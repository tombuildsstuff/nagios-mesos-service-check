#!/usr/bin/env python
import nagiosplugin
import argparse
import logging
import re
import requests
from discovery_state import DiscoveryState

log = logging.getLogger("nagiosplugin")
INFINITY = float('inf')
HEALTHY = 1
UNHEALTHY = -1

class MesosHealthCheck(nagiosplugin.Resource):
  def __init__(self, name, service_uri, endpoint, metric_name, timeout):
    self.myname = name
    self.service_uri = service_uri
    self.endpoint = endpoint
    self.metric_name = metric_name
    self.timeout = timeout

  @property
  def name(self):
    return self.myname + ' ' + self.endpoint

  def probe(self):
    try:
      endpoint_to_check = self.service_uri + self.endpoint
      log.debug('Checking %s', endpoint_to_check)
      response = requests.get(endpoint_to_check, timeout=float(self.timeout))
      if not response.status_code in [200, 204]:
        log.error('%s health %s: %s', self.metric_name, response.status_code, response.text)
        yield nagiosplugin.Metric(self.metric_name, UNHEALTHY)
      else:
        log.debug('%s health %s: %s', self.metric_name, response.status_code, response.text)
        yield nagiosplugin.Metric(self.metric_name, HEALTHY)
    except requests.exceptions.RequestException, e:
      log.error('%s health %s', self.metric_name, e)
      yield nagiosplugin.Metric(self.metric_name, UNHEALTHY)

@nagiosplugin.guarded
def main():
  argp = argparse.ArgumentParser()
  argp.add_argument('-d', '--discovery', required=True,
                    help='The URL of the discovery server')
  argp.add_argument('-s', '--service', required=True,
                    help='The service name to check')
  argp.add_argument('-e', '--endpoint', default='/health',
                    help='The endpoint to check')
  argp.add_argument('-t', '--timeout', default=5,
                    help='Timeout')
  argp.add_argument('-n', '--instances', default=1,
                    help='Minimum instances before critical')
  argp.add_argument('-w', '--warn', default=-1,
                    help='Minimum instances before warn')
  argp.add_argument('-v', '--verbose', action='count', default=0,
                    help='increase output verbosity (use up to 3 times)')

  args = argp.parse_args()

  unhealthy_range = nagiosplugin.Range('%d:%d' % (HEALTHY - 1, HEALTHY + 1))
  warn_services_range = nagiosplugin.Range('%s:' % (args.warn,))
  crit_services_range = nagiosplugin.Range('%s:' % (args.instances,))

  try:
    discovery_state = requests.get(args.discovery + '/state', timeout=4).json()
  except ValueError, e:
    log.error('ValueError while parsing discovery state: %s', e)
    discovery_state = []
  announcements = [a for a in discovery_state if a['serviceType'] == args.service]

  check = nagiosplugin.Check(
              DiscoveryState(args.service, announcements),
              nagiosplugin.ScalarContext('announced services', warn_services_range, crit_services_range))

  for ann in announcements:
    name = 'service %s instance %s' % (ann['serviceType'], ann['serviceUri'])
    check.add(MesosHealthCheck(args.service, ann['serviceUri'], args.endpoint, name, args.timeout),
              nagiosplugin.ScalarContext(name, unhealthy_range, unhealthy_range))

  check.main(verbose=args.verbose)

if __name__ == '__main__':
  main()
