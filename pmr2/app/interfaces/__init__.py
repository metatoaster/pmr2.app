import zope.deprecation
import zope.schema
import zope.interface

from zope.i18nmessageid import MessageFactory
_ = MessageFactory("pmr2")

from pmr2.app.schema import ObjectId
from pmr2.app.interfaces.exceptions import *

from pmr2.app.settings.interfaces import IPMR2GlobalSettings

zope.deprecation.deprecated('IPMR2GlobalSettings',
    'Please run migration script for pmr2.app-0.4 before 0.5 is installed.')

__all__ = [
    'IPMR2AppLayer',
    'IExposureContentIndex',
    'IExposureSourceAdapter',
    'IPMR2KeywordProvider',
]


# Interfaces

class IPMR2AppLayer(zope.interface.Interface):
    """\
    Marker interface for this product.
    """


class IExposureContentIndex(zope.interface.Interface):
    """\
    Interface for methods that will return a workable index.  All 
    exposure objects need to implement this to make catalog contain data
    that will make sense for presentation.

    Basically acquisition of parent methods by child will cause the
    child to be indexed, causing pollution of index and complication in 
    querying.

    Ideally this interface should not have to exist, if the catalog/
    indexing tools are more flexible in allowing what kind of data to 
    include for an object.  Implementation of this class is only a 
    demonstration of what I intend to do, which is to have subobjects
    hold into the keys they hold onto, but the URI will be taken to the
    parent object, and subobjects do not have keys to the parent object.

    Yes, this interface and implementation is a giant workaround of the
    flaws in ZCatalog and how Plone use them.  Unfortunately at this
    stage it is faster to workaround their issues than to roll our own
    cataloging solution based on zope.app.catalog (or RDF store, which
    is in the future).
    """

    def get_authors_family_index():
        pass

    def get_citation_title_index():
        pass

    def get_curation_index():
        pass

    def get_keywords_index():
        pass

    def get_exposure_workspace_index():
        pass


class IExposureSourceAdapter(zope.interface.Interface):
    """\
    Provides any Exposure related objects with methods that will return
    its source Exposure (root), the Workspace object, the relative path
    within it and the content of the file.
    """

    def source():
        """\
        returns a tuple containing its root exposure object, workspace 
        object and the full path of the actual file in this order.
        """

    def file():
        """\
        returns the string of the file itself.
        """


class IPMR2KeywordProvider(zope.interface.Interface):
    """\
    A provider of keywords that are captured from the object.

    Even though currently notes are the primary provider of data, which
    by extension provides the keywords for a particular file, the 
    indexed terms will be anchored on the parent object rather than the
    note.  If a note wish to manually be referenced it must generate the
    right values which can uniquely identify the note, and the view must
    be overridden to link to the intended results.
    """
