import json
import urllib
from urlparse import urljoin
import requests
from cloudfoundry.apps import CloudFoundryApp
from cloudfoundry.services import CloudFoundryService
import os
import logging
import pprint


class CloudFoundryException(Exception):
    pass


class CloudFoundryAuthenticationException(CloudFoundryException):
    pass


class CloudFoundryInterface(object):
    token_file = '~/.vmc_token'

    def __init__(self, target, username=None, password=None, store_token=False, debug=False):
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

        logging.debug("Login Mode: {}".format(login_mode))
        if data and not login_mode:
            data = json.dumps(data)
        full_url = urljoin(self.target, url)
        if host_override:
            full_url = urljoin(host_override, url)
            logging.debug("Setting URL with host override: {}".format(full_url))
        response = request_type(full_url, verify=verify, data=data, **self.auth_args(authentication_required,login_mode=login_mode))
        if self.debug:
            logging.debug("Request Body: {}".format(response.request.url))
            logging.debug("Response Body: {}".format(response.text))
        if response.status_code == 200:
            return response
        elif response.status_code == 403:
            if not authentication_required:
                raise CloudFoundryAuthenticationException(response.text)
            else:
                self.login()
                return self._request(url, request_type, authentication_required=False, data=data)
        elif response.status_code == 404:
            raise CloudFoundryException("HTTP %s - %s" % (response.status_code, response.text))
        else:
            raise CloudFoundryException("HTTP %s - %s" % (response.status_code, response.text))

    def _get_json_or_exception(self, *args, **kwargs):
        return self._request(*args, **kwargs).json()

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

    def login(self):

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
        return True


    def get_apps(self):
        return [CloudFoundryApp.from_dict(app, self) for app in self._get_json_or_exception("v2/apps")]

        # def get_app(self, name):
        # return CloudFoundryApp.from_dict(self._get_json_or_exception("v2/apps/%s" % name), self)
        #
        # def get_app_crashes(self, name):
        #     return self._get_json_or_exception("v2/apps/%s/crashes" % name)
        #
        # def get_app_instances(self, name):
        #     return self._get_json_or_exception("apps/%s/instances" % name)
        #
        # def get_app_stats(self, name):
        #     return self._get_json_or_exception("apps/%s/stats" % name)
        #
        # def delete_app(self, name):
        #     return self._get_true_or_exception("apps/%s" % name, request_type=requests.delete)
        #
        # def get_services(self):
        #     return [CloudFoundryService.from_dict(service, self) for service in self._get_json_or_exception("services/")]
        #
        # def get_service(self, name):
        #     return CloudFoundryService.from_dict(self._get_json_or_exception("services/%s" % name), self)
        #
        # def delete_service(self, name):
        #     return self._get_true_or_exception("services/%s" % name, request_type=requests.delete)

