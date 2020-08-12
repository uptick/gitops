from configparser import ConfigParser


class GitopsConfigParser(ConfigParser):
    def getlist(self, section, option, *args, **kwargs):
        value = self.get(section, option, *args, **kwargs)
        return list(filter(None, (x.strip() for x in value.splitlines())))


_config = GitopsConfigParser()
_config.read('setup.cfg')

if not _config.has_section('gitops'):
    _config.add_section('gitops')
options = _config['gitops']
