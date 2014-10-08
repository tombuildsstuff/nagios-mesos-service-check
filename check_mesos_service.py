#!/usr/bin/env python
import nagiosplugin
import argparse
import logging
import re
import requests

log = logging.getLogger("nagiosplugin")

INFINITY = float('inf')
HEALTHY = 1
UNHEALTHY = -1

class MesosService(nagiosplugin.Resource):
  def __init__(self, service_uri, metric_name):
    self.service_uri = service_uri
    self.metric_name = metric_name

  def probe(self):
    try:
      response = requests.head(self.service_uri + '/health')
      if not response.status_code in [200, 204]:
        log.error('%s health %s: %s', self.metric_name, response.status_code, response.text)
        yield nagiosplugin.Metric(self.metric_name, UNHEALTHY)
      else:
        log.debug('%s health %s: %s', self.metric_name, response.status_code, response.text)
        yield nagiosplugin.Metric(self.metric_name, HEALTHY)
    except requests.exceptions.RequestException, e:
      log.error('%s health %s', self.metric_name, e)
      yield nagiosplugin.Metric(self.metric_name, UNHEALTHY)


class DiscoveryState(nagiosplugin.Resource):
  def __init__(self, announcements):
    self.announcements = announcements

  def probe(self):
    yield nagiosplugin.Metric('announced services', len(self.announcements))

@nagiosplugin.guarded
def main():
  argp = argparse.ArgumentParser()
  argp.add_argument('-d', '--discovery', required=True,
                    help='The URL of the discovery server')
  argp.add_argument('-s', '--service', required=True,
                    help='The service name to check')
  argp.add_argument('-n', '--instances', default=1,
                    help='The number of instances to check')
  argp.add_argument('-v', '--verbose', action='count', default=0,
                    help='increase output verbosity (use up to 3 times)')

  args = argp.parse_args()

  unhealthy_range = nagiosplugin.Range('%d:%d' % (HEALTHY - 1, HEALTHY + 1))
  n_services_range = nagiosplugin.Range('%s:' % (args.instances,))

  discovery_state = requests.get(args.discovery + '/state').json()
  announcements = [a for a in discovery_state if a['serviceType'] == args.service]

  check = nagiosplugin.Check(
              DiscoveryState(announcements),
              nagiosplugin.ScalarContext('announced services', n_services_range, n_services_range))

  for ann in announcements:
    name = 'service %s instance %s' % (ann['serviceType'], ann['serviceUri'])
    check.add(MesosService(ann['serviceUri'], name),
              nagiosplugin.ScalarContext(name, unhealthy_range, unhealthy_range))

  check.main(verbose=args.verbose)

if __name__ == '__main__':
  main()
