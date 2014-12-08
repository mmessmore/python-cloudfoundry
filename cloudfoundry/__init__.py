import json
import urllib
from urlparse import urljoin
import requests
from cloudfoundry.apps import CloudFoundryApp
from cloudfoundry.organizations import CloudFoundryOrg
from cloudfoundry.spaces import CloudFoundrySpace
from cloudfoundry.routes import CloudFoundryRoute
from cloudfoundry.domains import CloudFoundryDomain
from utils import create_bits_zip
from collections import OrderedDict
import logging
import time
from pprint import pprint,pformat


class CloudFoundryException(Exception):
    pass


class CloudFoundryAuthenticationException(CloudFoundryException):
    pass


class CloudFoundryInterface(object):
    token_file = '~/.vmc_token'



    def __init__(self, target, username=None, password=None, debug=False):
        self.apps = None
        self.orgs = None
        self.spaces = None
        self.routes = None
        self.domains = None
        self.expires_at = None

        self.target = target
        self.username = username
        self.password = password
        self.token = None
        self.auth_endpoint = None

        self.debug = debug



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

    def _request(self, url, request_type=requests.get, authentication_required=True, data=None, host_override=None, verify=False, login_mode=False, raw_data = False, files=None):

        if not self.live and authentication_required:
            raise CloudFoundryException("Auth Required and Not Logged In")

        logging.debug("Login Mode: {}".format(login_mode))
        if data and not (login_mode or raw_data):
            data = json.dumps(data)
        full_url = urljoin(self.target, url)
        if host_override:
            full_url = urljoin(host_override, url)
            logging.info("Setting URL with host override: {}".format(full_url))

        response = request_type(full_url, verify=verify, data=data, files=files, **self.auth_args(authentication_required,login_mode=login_mode))

        if response.status_code in range(200,299):
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

    def _get_or_exception(self, url, json=True, **kwargs):
        if json:
            return self._request(url, **kwargs).json()
        return self._request(url, **kwargs).text

    def _post_or_exception(self, url, json=True, **kwargs):
        if json:
            return self._request(url, request_type=requests.post, **kwargs).json()
        return self._request(url, request_type=requests.post, **kwargs).text

    def _delete_or_exception(self, url, json=True, **kwargs):
        if json:
            return self._request(url, request_type=requests.delete, **kwargs).json()
        return self._request(url, request_type=requests.delete, **kwargs).text

    def _put_or_exception(self, url, json=True, files=None, data=None, **kwargs):
        if json:
            return self._request(url, request_type=requests.put, files=files, data=data, **kwargs).json()
        return self._request(url, request_type=requests.put, files=files, data=data, **kwargs).text

    def _get_auth_endpoint(self):

        response = self._get_or_exception(
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

        response = self._get_or_exception(
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

        self.expires_at = int(response['expires_in']) + time.time()
        if not update_token:
            self.refresh_all()


    def refresh_all(self):
        if not self.live:
            self.login()
        self.apps = self._get_apps()
        self.orgs = self._get_orgs()
        self.spaces = self._get_spaces()
        self.routes = self._get_routes()
        self.domains = self._get_domains()

    def _get_orgs(self):
        raw = self._get_or_exception("v2/organizations")['resources']
        orgs = {}
        for org in raw:
            org_data = org['entity']
            metadata = org['metadata']
            current_org = CloudFoundryOrg.from_dict(metadata,org_data)
            orgs[current_org.guid] = current_org
        return orgs

    def _get_spaces(self):
        raw = self._get_or_exception("v2/spaces")['resources']
        spaces = {}
        for space in raw:
            space_data = space['entity']
            metadata = space['metadata']
            current_org = CloudFoundrySpace.from_dict(metadata,space_data)
            spaces[current_org.guid] = current_org
        return spaces

    def _get_domains(self):
        domains = {}
        shared_raw = self._get_or_exception("v2/shared_domains")['resources']
        for domain in shared_raw:
            domain_data = domain['entity']
            metadata = domain['metadata']
            current_domain = CloudFoundryDomain.from_dict(metadata,domain_data)
            domains[current_domain.guid] = current_domain

        private_raw = self._get_or_exception("v2/private_domains")['resources']
        for domain in private_raw:
            domain_data = domain['entity']
            metadata = domain['metadata']
            current_domain = CloudFoundryDomain.from_dict(metadata,domain_data)
            domains[current_domain.guid] = current_domain

        return domains



    def _get_apps(self):
        raw = self._get_or_exception("v2/apps")['resources']
        apps = {}
        for app in raw:
            app_data = app['entity']
            metadata = app['metadata']
            current_app = CloudFoundryApp.from_dict(metadata,app_data)
            apps[current_app.guid] = current_app
        return apps

    def _get_routes(self):
        raw = self._get_or_exception("v2/routes")['resources']
        routes = {}
        for route in raw:
            route_data = route['entity']
            metadata = route['metadata']
            current_route = CloudFoundryRoute.from_dict(metadata,route_data)
            routes[current_route.guid] = current_route
        return routes


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

        response = self._post_or_exception("v2/apps",data={'name':name, 'space_guid':space_guid})
        metadata = response['metadata']
        app_data = response['entity']
        app = CloudFoundryApp.from_dict(metadata,app_data)
        self.apps[app.guid] = app
        return app


    def delete_app(self,guid):
        logging.critical("Deleting App with GUID: {}".format(guid))

        response = self._delete_or_exception("v2/apps/{}".format(guid),json=False)
        self.apps.pop(guid,None)

    def upload_bits(self,app,path):
        assert isinstance(app, CloudFoundryApp)
        zipdata = create_bits_zip(path)
        files_data = OrderedDict()
        files_data['resources'] = (None,'[]')
        files_data['application'] = zipdata.getvalue()

        logging.debug(dict(files_data))

        self._put_or_exception("v2/apps/{}/bits".format(app.guid),
                               files=files_data,
                               raw_data = True
                               )

    def start_app(self,app):
        self.update_app(app,{'STATE':'STARTED'})

    def update_app(self,app,changes):
        assert isinstance(app, CloudFoundryApp)
        assert isinstance(changes,dict)
        self._put_or_exception("/v2/apps/{}?async=true".format(app.guid),
            data=changes,
        )
        self.apps = self._get_apps()




