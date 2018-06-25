import yaml


def parseYaml(file):
    """Function parsing a YAML file"""
    with open(file, 'r') as stream:
        data = yaml.load(stream)
    return data
