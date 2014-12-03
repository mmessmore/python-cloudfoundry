import json
import urllib
from urlparse import urljoin
import requests
from cloudfoundry.apps import CloudFoundryApp
from cloudfoundry.services import CloudFoundryService
from cloudfoundry.organizations import CloudFoundryOrg
from cloudfoundry.spaces import CloudFoundrySpace
import os
import logging
import time
from pprint import pprint,pformat


class CloudFoundryException(Exception):
    pass


class CloudFoundryAuthenticationException(CloudFoundryException):
    pass


class CloudFoundryInterface(object):
    token_file = '~/.vmc_token'



    def __init__(self, target, username=None, password=None, store_token=False, debug=False):
        self.apps = None
        self.orgs = None
        self.spaces = None
        self.expires_at = None

        self.target = target
        self.username = username
        self.password = password
        self.token = None
        self.auth_endpoint = None
        self.store_token = store_token
        self.debug = debug
        self.token_file = os.path.expanduser(self.token_file)

        if self.store_token:
            if os.path.exists(self.token_file):
                with open(self.token_file) as fobj:
                    try:
                        data = json.load(fobj)
                        if self.target in data:
                            self.token = data[self.target]
                    except ValueError:  # Invalid JSON in file, probably empty
                        pass

    def auth_args(self, authentication_required, login_mode=False):
        headers = {'Accept':'application/json'}
        headers.update({'Authorization': 'bearer {}'.format(self.token)})
        logging.debug("Basic Headers: {}".format(headers))
        if login_mode: # we have a special Auth header when we are logging in, with a static auth code
            headers.update({'Authorization': 'Basic Y2Y6'})
        if not authentication_required and not self.token:
            # return {'headers': headers}
            pass
        elif not self.token and self.store_token:  # Ignore, will request new token afterwards!
            # return {'headers': headers}
            pass
        elif not self.token:
            raise CloudFoundryAuthenticationException("Please login before using this function")

        logging.debug("Returning Final Headers: {}".format(headers))
        return {'headers': headers}

    def _request(self, url, request_type=requests.get, authentication_required=True, data=None, host_override=None, verify=False, login_mode=False):

        if not self.live and authentication_required:
            raise CloudFoundryException("Auth Required and Not Logged In")

        logging.debug("Login Mode: {}".format(login_mode))
        if data and not login_mode:
            data = json.dumps(data)
        full_url = urljoin(self.target, url)
        if host_override:
            full_url = urljoin(host_override, url)
            logging.info("Setting URL with host override: {}".format(full_url))

        response = request_type(full_url, verify=verify, data=data, **self.auth_args(authentication_required,login_mode=login_mode))

        if response.status_code == 200 or response.status_code == 201:
            return response
        elif response.status_code == 403:
            if not authentication_required:
                raise CloudFoundryAuthenticationException(response.text)
            else:
                self.login()
                return self._request(url, request_type, authentication_required=False, data=data)
        elif response.status_code == 404:
            raise CloudFoundryException("HTTP {} - {}".format(response.status_code, response.text))
        else:
            raise CloudFoundryException("HTTP {} - {}".format(response.status_code, response.text))

    def _get_json_or_exception(self, *args, **kwargs):
        return self._request(*args, **kwargs).json()

    def _post_json_or_exception(self, *args, **kwargs):
        return self._request(*args, request_type=requests.post, **kwargs).json()

    def _get_true_or_exception(self, *args, **kwargs):
        self._request(*args, **kwargs)
        return True

    def _get_auth_endpoint(self):

        response = self._get_json_or_exception(
            "v2/info",
            request_type=requests.get,
            authentication_required=False
        )


        # logging.debug(response)
        self.auth_endpoint = response['authorization_endpoint']
        logging.debug("Setting auth endpoint as {}".format(self.auth_endpoint))

        return self.auth_endpoint

    @property
    def live(self):
        current_time = time.time()
        if current_time > self.expires_at:
            return False
        return True

    def login(self,update_token=False):

        response = self._get_json_or_exception(
            "oauth/token",
            request_type=requests.post,
            authentication_required=False,
            host_override=self._get_auth_endpoint(),
            login_mode=True,
            data={
                "grant_type": "password",
                "password": self.password,
                "scope": "",
                "username": self.username
            }
        )

        self.token = response['access_token']

        if self.store_token:
            data = {self.target: self.token}
            if os.path.exists(self.token_file):
                try:
                    with open(self.token_file) as token_file:
                        data = json.loads(token_file.read())
                        data[self.target] = self.token
                except ValueError:  # Invalid JSON in file, probably empty
                    pass
            with open(self.token_file, 'w') as token_file:
                json.dump(data, token_file)

        self.expires_at = int(response['expires_in']) + time.time()
        if not update_token:
            self.refresh()


    def refresh(self):
        if not self.live:
            self.login()
        self.apps = self._get_apps()
        self.orgs = self._get_orgs()
        self.spaces = self._get_spaces()

    def _get_orgs(self):
        raw = self._get_json_or_exception("v2/organizations")['resources']
        orgs = {}
        for org in raw:
            org_data = org['entity']
            metadata = org['metadata']
            current_org = CloudFoundryOrg.from_dict(metadata,org_data)
            orgs[current_org.guid] = current_org
        return orgs

    def _get_spaces(self):
        raw = self._get_json_or_exception("v2/spaces")['resources']
        spaces = {}
        for space in raw:
            space_data = space['entity']
            metadata = space['metadata']
            current_org = CloudFoundrySpace.from_dict(metadata,space_data)
            spaces[current_org.guid] = current_org
        return spaces

    def _get_apps(self):
        raw = self._get_json_or_exception("v2/apps")['resources']
        apps = {}
        for app in raw:
            app_data = app['entity']
            metadata = app['metadata']
            current_app = CloudFoundryApp.from_dict(metadata,app_data)
            apps[current_app.guid] = current_app
        return apps

    def get_app(self,guid):
        if not self.live:
            self.login()
        if guid in self.apps.keys():
            return self.apps[guid]
        return None

    def get_app_by_name(self,name):
        for app in self.apps.values():
            if app.name == name:
                return app
        return None

    def create_app(self,name, space_guid):
        logging.warn("Creating new app in space {}".format(space_guid))

        response = self._post_json_or_exception("v2/apps",data={'name':name, 'space_guid':space_guid})
        metadata = response['metadata']
        app_data = response['entity']
        app = CloudFoundryApp.from_dict(metadata,app_data)
        self.apps[app.guid] = app
        return app

