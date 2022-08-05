import logging
import json
import re

import requests
from lxml import html

from ckan.plugins import toolkit
from ckan.plugins.core import SingletonPlugin, implements
from ckanext.harvest.interfaces import IHarvester
from ckan import model
from ckanext.harvest.model import HarvestObject

log = logging.getLogger(__name__)


def parse_count(document):
    element = document.cssselect("div.browse_range")[0]

    match = re.search(r"Anzeige der Treffer (\d+) bis (\d+) von (\d+)", element.text)
    if match:
        return int(match.group(3))


def parse_handles(document):
    handles = []

    for element in document.cssselect("td[headers=t2] > a"):
        handles.append(element.get("href"))

    return handles


def fetch_datasets(base_url, rpp, offset):
    url = base_url + "jspui/browse"

    response = requests.get(url, params={"rpp": rpp, "offset": offset})
    response.raise_for_status()
    response = response.text

    document = html.fromstring(response)

    count = parse_count(document)
    handles = parse_handles(document)

    return count, handles


def fetch_dataset(url):
    response = requests.get(url)
    response.raise_for_status()
    response = response.text

    document = html.fromstring(response)

    urn = None
    title = None
    description = None

    for element in document.cssselect("table.itemDisplayTable > tr"):
        label_elements = element.cssselect("td.metadataFieldLabel")
        if len(label_elements) == 0:
            continue

        value_elements = element.cssselect("td.metadataFieldValue > span")
        if len(value_elements) == 0:
            continue

        label = label_elements[0].text
        value = value_elements[0].text

        if not label or not value:
            continue

        label = label.strip()
        value = value.strip()

        if label == "URN(s):":
            urn = value
        elif label == "Titel:":
            title = value
        elif label == "Zusammenfassung:":
            description = value

    return json.dumps({"urn": urn, "title": title, "description": description})


def make_harvest_objects(harvest_job, ids, handles):
    for handle in handles:
        urn = handle[len("/jspui/handle/") :]
        guid = f"doris-bfs-{urn}"

        harvest_object = HarvestObject(
            guid=guid,
            job=harvest_job,
        )

        harvest_object.content = handle

        harvest_object.save()
        ids.append(harvest_object.id)


class DorisBfSHarvester(SingletonPlugin):
    implements(IHarvester)

    def info(self):
        return {
            "name": "doris_bfs",
            "title": "Doris (BfS)",
            "description": "Digitale Dokumente des Bundesamtes für Strahlenschutz",
        }

    def gather_stage(self, harvest_job):
        base_url = harvest_job.source.url
        rpp = 10

        count, handles = fetch_datasets(base_url, rpp, 0)

        log.debug("Gathering %d documents from %s", count, base_url)

        # TODO: diff this against what is already in the database
        ids = []

        make_harvest_objects(harvest_job, ids, handles)

        num_requests = (count + rpp - 1) // rpp

        for request in range(1, num_requests):
            offset = request * rpp

            _, handles = fetch_datasets(base_url, rpp, offset)

            make_harvest_objects(harvest_job, ids, handles)

        return ids

    def fetch_stage(self, harvest_object):
        base_url = harvest_object.job.source.url
        url = base_url + harvest_object.content

        log.debug("Fetching document from %s", url)

        harvest_object.content = fetch_dataset(url)
        harvest_object.add()

        return True

    def import_stage(self, harvest_object):
        content = json.loads(harvest_object.content)

        package_dict = {
            "name": content["urn"].replace(":", "_"),
            "title": content["title"],
            "notes": content["description"],
            "tags": [],
            "resources": [],
            "extras": [
                {"key": "harvest_object_id", "value": harvest_object.id},
                {"key": "harvest_source_id", "value": harvest_object.job.source.id},
                {
                    "key": "harvest_source_title",
                    "value": harvest_object.job.source.title,
                },
            ],
        }

        source_dataset = model.Package.get(harvest_object.source.id)
        if source_dataset.owner_org:
            log.debug("Owner org is %s", source_dataset.owner_org)
            package_dict["owner_org"] = source_dataset.owner_org

        context = {
            "model": model,
            "session": model.Session,
            "ignore_auth": True,
            "defer_commit": True,  # See ckan/ckan#1714
        }

        # TODO: get the correct user for the harvest object
        site_user = toolkit.get_action("get_site_user")(context, {})
        log.debug("Site user is %s", site_user["name"])

        context = {
            "model": model,
            "session": model.Session,
            "user": site_user["name"],
            "ignore_auth": True,
        }

        package_dict = toolkit.get_action("package_create")(context, package_dict)
        log.info(
            "Created new package %s with guid %s",
            package_dict["id"],
            harvest_object.guid,
        )

        return True
