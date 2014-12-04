# Python-Cloudfoundry2

Sample usage:
```python
from cloudfoundry import CloudFoundryInterface

cfi = CloudFoundryInterface(target=api,username=username,password=password,debug=True)
cfi.login()
pprint(cfi.all_apps)
myapp = cfi.get_app_by_name("chargers")
print(myapp)
print(cfi.spaces)
new_app = cfi.create_app("api-test-app",cfi.spaces.keys()[0])
pprint(new_app)
cfi.delete_app(new_app.guid)
```

Originally based on python-cloudfoundry from (https://github.com/KristianOellegaard/python-cloudfoundry), bit updates to support v2 and other changes/additions.