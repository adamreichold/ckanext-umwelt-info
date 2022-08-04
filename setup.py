from setuptools import setup, find_packages

setup(
    name="ckanext-umwelt-info",
    version="0.1.0",
    description="CKAN plug-ins for the umwelt.info project",
    long_description="""\
    """,
    classifiers=[],
    keywords="",
    author="umwelt-info",
    author_email="umwelt.info@uba.de",
    url="https://umwelt.info",
    license="AGPL",
    packages=find_packages(),
    namespace_packages=["ckanext"],
    entry_points="""
        [ckan.plugins]
        wasser_de_harvester=ckanext.umwelt_info.harvesters:WasserDEHarvester
    """,
)
