# Python-Cloudfoundry

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

