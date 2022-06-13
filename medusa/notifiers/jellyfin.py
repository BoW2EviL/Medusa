# coding=utf-8

"""Jellyfin notifier module."""
from __future__ import unicode_literals

import json
import logging

from medusa import app
from medusa.helper.exceptions import ex
from medusa.indexers.config import INDEXER_TVDBV2, INDEXER_TVRAGE
from medusa.indexers.utils import indexer_id_to_name, mappings
from medusa.logger.adapters.style import BraceAdapter
from medusa.session.core import MedusaSession

from requests.exceptions import HTTPError, RequestException

from six import text_type

log = BraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class Notifier(object):
    """Jellyfin notifier class."""

    def __init__(self):
        self.session = MedusaSession()

    def _notify_jellyfin(self, message, host=None, jellyfin_apikey=None):
        """
        Notify Jellyfin host via HTTP API.

        :return: True for no issue or False if there was an error
        """
        # fill in omitted parameters
        if not host:
            host = app.JELLYFIN_HOST
        if not jellyfin_apikey:
            jellyfin_apikey = app.JELLYFIN_APIKEY

        url = 'http://{host}/Notifications/Admin'.format(host=host)
        data = json.dumps({
            'Name': 'Medusa',
            'Description': message,
            'ImageUrl': app.LOGO_URL
        })
        try:
            resp = self.session.post(
                url=url,
                data=data,
                headers={
                    'X-MediaBrowser-Token': jellyfin_apikey,
                    'Content-Type': 'application/json'
                }
            )
            resp.raise_for_status()

            if resp.text:
                log.debug('JELLYFIN: HTTP response: {0}', resp.text.replace('\n', ''))

            log.info('JELLYFIN: Successfully sent a test notification.')
            return True

        except (HTTPError, RequestException) as error:
            log.warning('JELLYFIN: Warning: Unable to contact Jellyfin at {url}: {error}',
                        {'url': url, 'error': ex(error)})
            return False

##############################################################################
# Public functions
##############################################################################

    def test_notify(self, host, jellyfin_apikey):
        """
        Sends a test notification.

        :return: True for no issue or False if there was an error
        """
        return self._notify_jellyfin('This is a test notification from Medusa', host, jellyfin_apikey)

    def update_library(self, show=None):
        """
        Update the Jellyfin Media Server host via HTTP API.

        :return: True for no issue or False if there was an error
        """
        if app.USE_JELLYFIN:
            if not app.JELLYFIN_HOST:
                log.debug('JELLYFIN: No host specified, check your settings')
                return False

            if show:
                # JELLYFIN only supports TVDB ids
                provider = 'tvdbid'
                if show.indexer == INDEXER_TVDBV2:
                    tvdb_id = show.indexerid
                else:
                    # Try using external ids to get a TVDB id
                    tvdb_id = show.externals.get(mappings[INDEXER_TVDBV2], None)

                if tvdb_id is None:
                    if show.indexer == INDEXER_TVRAGE:
                        log.warning('JELLYFIN: TVRage indexer no longer valid')
                    else:
                        log.warning(
                            'JELLYFIN: Unable to find a TVDB ID for {series},'
                            ' and {indexer} indexer is unsupported',
                            {'series': show.name, 'indexer': indexer_id_to_name(show.indexer)}
                        )
                    return False

                url = 'http://{host}/Library/Series/Updated'.format(host=app.JELLYFIN_HOST)
                params = {
                    provider: text_type(tvdb_id)
                }
            else:
                url = 'http://{host}/Library/Refresh'.format(host=app.JELLYFIN_HOST)
                params = {}

            try:
                resp = self.session.post(
                    url=url,
                    params=params,
                    headers={
                        'X-MediaBrowser-Token': app.JELLYFIN_APIKEY
                    }
                )
                resp.raise_for_status()

                if resp.text:
                    log.debug('JELLYFIN: HTTP response: {0}', resp.text.replace('\n', ''))

                log.info('JELLYFIN: Successfully sent a "Series Library Updated" command.')
                return True

            except (HTTPError, RequestException) as error:
                log.warning('JELLYFIN: Warning: Unable to contact Jellyfin at {url}: {error}',
                            {'url': url, 'error': ex(error)})
                return False
