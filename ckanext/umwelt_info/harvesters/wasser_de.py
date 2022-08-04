import logging

from ckan.plugins.core import SingletonPlugin, implements
from ckanext.harvest.interfaces import IHarvester


class WasserDEHarvester(SingletonPlugin):
    implements(IHarvester)

    def info(self):
        return {
            "name": "wasser_de",
            "title": "Wasser-DE",
            "description": "Zentraler Informationsknoten Wasserwirtschaft Deutschland",
        }

    def gather_stage(self, harvest_job):
        return []

    def fetch_stage(self, harvest_object):
        return "unchanged"

    def import_stage(self, harvest_object):
        return "unchanged"
