#!/usr/bin/env python

# Tool to update the manifest.xml will the correct datetime of bundle creation
# as well as add git sha and bamboo build metadata
# FIXME copied from chemistry-data-bundle; we need a way to share this

import sys
import os
import argparse
import json
import subprocess
import datetime

from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

__version__ = "0.1.1"


class Constants(object):
    # there's an Id versus name issue here
    ID = "pbpipeline-resources"
    NAME = "SMRT Link pipeline resources"
    AUTHOR = "build"
    DESC = """Pipelines and view rules for SMRT Link and pbsmrtpipe"""


def get_parser():
    desc = "Update the manifest.xml"
    p = argparse.ArgumentParser(version=__version__,
                                description=desc,
                                formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("version_txt", help="Path to Manifest.xml")
    p.add_argument("-o", dest="output_manifest_xml", default="manifest.xml",
                   help="Path to the version.txt file. Must have a single line with Major.Minor.Tiny format")
    p.add_argument("-j", dest="pacbio_manifest_json", default="pacbio-manifest.json",
                   help="Output path output manifest JSON used by SMRT Link")
    p.add_argument('--author', dest="author",
                   default=Constants.AUTHOR, help="Bundle creation Author")
    return p


def git_short_sha():
    args = "git rev-parse --short HEAD".split()
    return subprocess.check_output(args).strip()


def get_bamboo_buildnumber(default="0000"):
    return os.environ.get('bamboo_globalBuildNumber', default)


def to_semver(major, minor, patch, git_sha, build_number=None, prerelease_tag=None):
    """Convert to semver format"""
    base = ".".join(str(i) for i in (major, minor, patch))
    prerelease = "" if prerelease_tag is None else "-{}".format(prerelease_tag)
    # need the trailing . as the sep for the other metadata
    number = "" if build_number is None else str(build_number) + "."
    metadata = "+{b}{s}".format(b=number, s=git_sha[:7])
    return "{b}{p}{m}".format(b=base, p=prerelease, m=metadata)


def to_undocumented_pacbio_version_format(major, minor, tiny, other):
    return ".".join([str(i) for i in (major, minor, tiny, other)])


def get_version(major, minor, tiny):
    build_number = get_bamboo_buildnumber()
    git_sha = git_short_sha()
    return to_semver(major, minor, tiny, git_sha, build_number=build_number)


def read_version_txt(path):
    with open(path, 'r') as f:
        x = f.readline()

    major, minor, tiny = [int(i) for i in x.split(".")][:3]
    return major, minor, tiny


def to_pacbio_manifest_d(version, desc):
    return dict(id=Constants.ID,
                name=Constants.NAME,
                version=version,
                description=desc,
                dependencies=[])


def prettify(elem):
    return minidom.parseString(tostring(elem, 'utf-8')).toprettyxml(indent="  ")


def write_manifest_xml(version, description, author, manifest_xml):

    root = Element("Manifest")

    def sub(n, value_):
        e = SubElement(root, n)
        e.text = value_
        return e

    sub("Package", Constants.ID)
    sub("Name", Constants.NAME)
    sub("Version", version)
    sub("Created", datetime.datetime.utcnow().isoformat())
    sub("Author", author)
    sub("Description", description)

    with open(manifest_xml, 'w') as f:
        f.write(prettify(root))

    return root


def write_pacbio_manifest_json(version, desc, output_json):
    with open(output_json, 'w') as f:
        f.write(json.dumps(to_pacbio_manifest_d(version, desc), indent=True))


def runner(version_txt, output_manifest_xml, pacbio_manifest_json, author):

    major, minor, tiny = read_version_txt(version_txt)
    sem_ver = get_version(major, minor, tiny)
    other = get_bamboo_buildnumber()
    version_str = to_undocumented_pacbio_version_format(
        major, minor, tiny, other)

    # this is to get the data propagated to SL services
    author = "User {} created pbpipeline-resources bundle {}".format(
        Constants.AUTHOR, sem_ver)

    # there's some tragic duplication of models between ICS and Secondary
    # hence this duplication of these very similar ideas
    write_manifest_xml(version_str, Constants.DESC,
                       author, output_manifest_xml)
    write_pacbio_manifest_json(
        version_str, Constants.DESC, pacbio_manifest_json)

    return 0


def main(argv_):
    p = get_parser()
    args = p.parse_args(argv_)
    return runner(args.version_txt, args.output_manifest_xml, args.pacbio_manifest_json, args.author)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
