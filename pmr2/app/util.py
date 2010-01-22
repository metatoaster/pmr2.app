import re
import os.path
from lxml import etree

from zope.component import getUtility
from Acquisition import aq_inner, aq_parent

import pmr2.mercurial.utils
from pmr2.app.interfaces import IPMR2GetPath
from pmr2.app.settings import IPMR2GlobalSettings

CELLML_NSMAP = {
    'tmpdoc': 'http://cellml.org/tmp-documentation',
    'pcenv': 'http://www.cellml.org/tools/pcenv/',
    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
}

def set_xmlbase(xml, base):
    try:
        dom = etree.fromstring(xml)
    except:
        # silently aborting on invalid input.
        return xml
    dom.set('{http://www.w3.org/XML/1998/namespace}base', base)
    result = etree.tostring(dom, encoding='utf-8', xml_declaration=True)
    return result

def fix_pcenv_externalurl(xml, base):
    """
    A workaround for PCEnv session specification bug
    https://tracker.physiomeproject.org/show_bug.cgi?id=1079

    Briefly, pcenv:externalurl is really a URI reference, but it is
    represented as a literal string, hence it does not benefit from
    the declaration of xml:base.

    this manually replaces externalurl with the xml:base fragment 
    inserted in front of it.
    """

    try:
        dom = etree.fromstring(xml)
    except:
        # silently aborting on invalid input.
        return xml

    externalurl = '{http://www.cellml.org/tools/pcenv/}externalurl'

    # RDF representation generated by PCEnv
    xulnodes = dom.xpath('.//rdf:Description[@pcenv:externalurl]',
        namespaces=CELLML_NSMAP)
    for node in xulnodes:
        xulname = node.xpath('string(@pcenv:externalurl)', 
            namespaces=CELLML_NSMAP)
        if xulname:
            node.attrib[externalurl] = '/'.join([base, xulname])

    # Different form of RDF presentation
    xulnodes = dom.xpath('.//pcenv:externalurl',
        namespaces=CELLML_NSMAP)
    for node in xulnodes:
        xulname = node.text
        if xulname:
            node.text = '/'.join([base, xulname])

    result = etree.tostring(dom, encoding='utf-8', xml_declaration=True)
    return result

uri_prefix = {
    'info:pmid/': 'http://www.ncbi.nlm.nih.gov/pubmed/%s',
    'urn:miriam:pubmed:': 'http://www.ncbi.nlm.nih.gov/pubmed/%s',
}

def uri2http(uri):
    """\
    Resolves an info-uri into an http link based on the lookup table 
    above.
    """

    # XXX need a way to normalize these uris into string
    try:
        uri = str(uri)
    except:
        uri = uri.decode('utf8', 'replace')

    for k, v in uri_prefix.iteritems():
        if uri.startswith(k):
            return v % uri[len(k):]
    return None

def obfuscate(input):
    try:
        text = input.decode('utf8')
    except UnicodeDecodeError:
        text = input
    return ''.join(['&#%d;' % ord(c) for c in text])

def short(input):
    return pmr2.mercurial.utils.filter(input, 'short')

def isodate(input):
    return pmr2.mercurial.utils.filter(input, 'isodate')

def normal_kw(input):
    """\
    Method to normalize keywords so we don't have to deal with cases
    when searching and allow the usage of spaces to delimit terms.
    """

    return input.strip().replace(' ', '_').lower()

re_simple_date = re.compile('^[0-9]{4}(-[0-9]{2}){0,2}')
def simple_valid_date(input):
    try:
        return re_simple_date.search(input)
    except:
        return False

def get_path(context, id):
    """\
    Deprecated method to get the filesystem path of a given context.
    """

    p = getUtility(IPMR2GlobalSettings)
    return p.dirCreatedFor(context)
