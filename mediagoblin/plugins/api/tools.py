# GNU MediaGoblin -- federated, autonomous media hosting
# Copyright (C) 2011, 2012 MediaGoblin contributors.  See AUTHORS.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import json

from functools import wraps
from urlparse import urljoin
from werkzeug.exceptions import Forbidden
from werkzeug.wrappers import Response
from mediagoblin import mg_globals
from mediagoblin.tools.pluginapi import PluginManager
from mediagoblin.storage.filestorage import BasicFileStorage

_log = logging.getLogger(__name__)


class Auth(object):
    '''
    An object with two significant methods, 'trigger' and 'run'.

    Using a similar object to this, plugins can register specific
    authentication logic, for example the GET param 'access_token' for OAuth.

    - trigger: Analyze the 'request' argument, return True if you think you
      can handle the request, otherwise return False
    - run: The authentication logic, set the request.user object to the user
      you intend to authenticate and return True, otherwise return False.

    If run() returns False, an HTTP 403 Forbidden error will be shown.

    You may also display custom errors, just raise them within the run()
    method.
    '''
    def trigger(self, request):
        raise NotImplemented()

    def __call__(self, request, *args, **kw):
        raise NotImplemented()


def json_response(serializable, _disable_cors=False, *args, **kw):
    '''
    Serializes a json objects and returns a werkzeug Response object with the
    serialized value as the response body and Content-Type: application/json.

    :param serializable: A json-serializable object

    Any extra arguments and keyword arguments are passed to the
    Response.__init__ method.
    '''
    response = Response(json.dumps(serializable), *args, content_type='application/json', **kw)

    if not _disable_cors:
        cors_headers = {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, X-Requested-With'}
        (response.headers.set(key, value) for key, value in cors_headers)

    return response


def get_entry_serializable(entry, urlgen):
    '''
    Returns a serializable dict() of a MediaEntry instance.

    :param entry: A MediaEntry instance
    :param urlgen: An urlgen instance, can be found on the request object passed
    to views.
    '''
    return {
            'user': entry.get_uploader.username,
            'user_id': entry.get_uploader.id,
            'user_bio': entry.get_uploader.bio,
            'user_bio_html': entry.get_uploader.bio_html,
            'user_permalink': urlgen('mediagoblin.user_pages.user_home',
                user=entry.get_uploader.username,
                qualified=True),
            'id': entry.id,
            'created': entry.created.isoformat(),
            'title': entry.title,
            'license': entry.license,
            'description': entry.description,
            'description_html': entry.description_html,
            'media_type': entry.media_type,
            'state': entry.state,
            'permalink': entry.url_for_self(urlgen, qualified=True),
            'media_files': get_media_file_paths(entry.media_files, urlgen)}


def get_media_file_paths(media_files, urlgen):
    '''
    Returns a dictionary of media files with `file_handle` => `qualified URL`

    :param media_files: dict-like object consisting of `file_handle => `listy
    filepath` pairs.
    :param urlgen: An urlgen object, usually found on request.urlgen.
    '''
    media_urls = {}

    for key, val in media_files.items():
        if isinstance(mg_globals.public_store, BasicFileStorage):
            # BasicFileStorage does not provide a qualified URI
            media_urls[key] = urljoin(
                    urlgen('index', qualified=True),
                    mg_globals.public_store.file_url(val))
        else:
            media_urls[key] = mg_globals.public_store.file_url(val)

    return media_urls


def api_auth(controller):
    '''
    Decorator, allows plugins to register auth methods that will then be
    evaluated against the request, finally a worthy authenticator object is
    chosen and used to decide whether to grant or deny access.
    '''
    @wraps(controller)
    def wrapper(request, *args, **kw):
        auth_candidates = []

        for auth in PluginManager().get_hook_callables('auth'):
            _log.debug('Plugin auth: {0}'.format(auth))
            if auth.trigger(request):
                auth_candidates.append(auth)

        # If we can't find any authentication methods, we should not let them
        # pass.
        if not auth_candidates:
            raise Forbidden()

        # For now, just select the first one in the list
        auth = auth_candidates[0]

        _log.debug('Using {0} to authorize request {1}'.format(
            auth, request.url))

        if not auth(request, *args, **kw):
            if getattr(auth, 'errors', []):
                return json_response({
                        'status': 403,
                        'errors': auth.errors})

            raise Forbidden()

        return controller(request, *args, **kw)

    return wrapper
