import logging
import json

import requests

from ckan.plugins import toolkit
from ckan.plugins.core import SingletonPlugin, implements
from ckanext.harvest.interfaces import IHarvester


log = logging.getLogger(__name__)


class WasserDEHarvester(SingletonPlugin):
    implements(IHarvester)

    def info(self):
        return {
            "name": "wasser_de",
            "title": "Wasser-DE",
            "description": "Zentraler Informationsknoten Wasserwirtschaft Deutschland",
        }

    def gather_stage(self, harvest_job):
        url = (
            harvest_job.source.url
            + "rest/BaseController/FilterElements/V_REP_BASE_VALID"
        )
        log.debug("Gathering documents from %s", url)

        response = requests.post(url, json={"filter": {}})
        response.raise_for_status()
        response = response.json()

        count = len(response["V_REP_BASE_VALID"])
        log.debug("Retrieved %d documents from %s", count, url)

        # TODO: diff this against what is already in the database
        ids = []

        for document in response["V_REP_BASE_VALID"]:
            if not document["NAME"]:
                continue

            id = document["ID"]
            guid = f"wasser-de-{id}"

            harvest_object = HarvestObject(
                guid=guid,
                job=harvest_job,
            )

            harvest_object.content = json.dumps(document)

            harvest_object.save()
            ids.append(harvest_object.id)

        return ids

    def fetch_stage(self, harvest_object):
        # Nothing to do since the document is already stored in the harvest object
        return True

    def import_stage(self, harvest_object):
        document = json.loads(harvest_object.content)

        id = document["ID"]
        title = document["NAME"]
        description = document["TEASERTEXT"] or document["AUTOTEASERTEXT"] or ""

        log.debug("Importing document %d", id)

        context = {
            "model": model,
            "session": model.Session,
            "ignore_auth": True,
            "defer_commit": True,  # See ckan/ckan#1714
        }

        # TODO: get the correct user for the harvest object
        site_user = toolkit.get_action("get_site_user")(context, {})

        context = {
            "model": model,
            "session": model.Session,
            "user": site_user["name"],
            "ignore_auth": True,
        }

        # TODO: create package_dict
        # TODO: create package

        return "unchanged"
