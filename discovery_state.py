import nagiosplugin
import logging

log = logging.getLogger("nagiosplugin")
TOKEN = "server-token"

class DiscoveryState(nagiosplugin.Resource):
  def __init__(self, name, announcements):
    self.myname = name
    self.announcements = announcements

  @property
  def name(self):
    return self.myname + ' announcement'

  def probe(self):
    seen = set()
    count = 0
    for ann in self.announcements:
      metadata = ann.get("metadata", dict())
      if TOKEN in metadata:
        token = metadata[TOKEN]
        if token not in seen:
          seen.add(token)
          log.debug('New token %s' % token)
          count += 1
        else:
          log.debug('Seen token %s' % token)
      else:
        log.debug('No token for service %s' % ann['announcementId'])
        count += 1
    yield nagiosplugin.Metric('announced services', count)
