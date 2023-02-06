import yaml

with open('./whitelist.yaml') as file:
    obj = yaml.safe_load(file)
    print(obj['whitelist'])
    w = obj['whitelist']

for x in w:
    print(x["rootlib"])