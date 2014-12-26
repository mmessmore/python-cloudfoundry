# Python-Cloudfoundry2

Simple installation (until this is submitted to PyPI at least):
```
pip install git+git://github.com/mcowger/python-cloudfoundry.git
```

Sample usage:
```python
from cloudfoundry import CloudFoundryInterface

cfi = CloudFoundryInterface(target=api.run.pivotak.io,username=username,password=password,debug=True)
cfi.login()
myapp = cfi.get_app_by_name("chargers")
print(myapp)
print(cfi.spaces)
new_app = cfi.create_app("api-test-app",cfi.spaces.keys()[0])
pprint(new_app)
cfi.delete_app(new_app.guid)
```

Originally based on python-cloudfoundry from (https://github.com/KristianOellegaard/python-cloudfoundry), bit updates to support v2 and other changes/additions.

Currently implemented are models of Apps, Spaces and Organizations.  Additionally, create and delete of apps is supported.  Note: by default, the library uses PyMemoize to cache the responses from CF for 10s for certain operations (mainly updating the current list of applications, spaces, etc).  This can be adjusted, and invalidation of the cache is handled when using the module to make changes (creating routes, etc).

TODO (in approx. order):
* Tests!
* modeling for buildpacks
* Modeling for Services
* Service binding to apps
* User management
