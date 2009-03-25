from zope.interface import alsoProvides
from zope.component import getUtilitiesFor

from zope.schema.interfaces import IVocabularyFactory, ISource
from zope.schema.vocabulary import SimpleVocabulary, SimpleTerm

from Products.CMFCore.utils import getToolByName

from pmr2.app.interfaces import IExposureDocumentFactory


class WorkspaceDirObjListVocab(SimpleVocabulary):

    def __init__(self, context):
        self.context = context
        values = self.context.get_repository_list()
        terms = [SimpleTerm(i, i[0]) for i in values]
        super(WorkspaceDirObjListVocab, self).__init__(terms)


def WorkspaceDirObjListVocabFactory(context):
    return WorkspaceDirObjListVocab(context)

alsoProvides(WorkspaceDirObjListVocabFactory, IVocabularyFactory)


class ManifestListVocab(SimpleVocabulary):

    def __init__(self, context):
        self.context = context
        values = self.context.get_manifest()
        terms = [SimpleTerm(i, i) for i in values]
        super(ManifestListVocab, self).__init__(terms)


def ManifestListVocabFactory(context):
    return ManifestListVocab(context)

alsoProvides(ManifestListVocabFactory, IVocabularyFactory)


class PMR2TransformsVocab(SimpleVocabulary):

    def __init__(self, context):
        self.context = context
        pt = getToolByName(context, 'portal_transforms')
        transforms = [(i, getattr(pt, i).get_documentation().strip()) \
                for i in pt.objectIds() if i.startswith('pmr2_processor_')]
        transforms.sort()
        terms = [SimpleTerm(*i) for i in transforms]
        super(PMR2TransformsVocab, self).__init__(terms)


def PMR2TransformsVocabFactory(context):
    return PMR2TransformsVocab(context)

alsoProvides(PMR2TransformsVocabFactory, IVocabularyFactory)


class PMR2IndexesVocab(SimpleVocabulary):

    def __init__(self, context):
        self.context = context
        self.pt = None
        try:
            # If the context passed into here is unbounded, it won't have
            # a catalog to valudate against.
            self.pt = getToolByName(context, 'portal_catalog')
            values = self.pt.indexes()
        except:
            values = []
        terms = [SimpleTerm(i) for i in values if i.startswith('pmr2_')]
        super(PMR2IndexesVocab, self).__init__(terms)

    def getTerm(self, value):
        if self.pt is None:
            # no portal tool, see __init__
            return SimpleTerm(value)
        else:
            return super(PMR2IndexesVocab, self).getTerm(value)

    def __contains__(self, terms):
        if self.pt is None:
            # no portal tool, see __init__
            return True
        else:
            return super(PMR2IndexesVocab, self).__contains__(terms)


def PMR2IndexesVocabFactory(context):
    return PMR2IndexesVocab(context)

alsoProvides(PMR2IndexesVocabFactory, IVocabularyFactory)


class PMR2ExposureDocumentFactoryVocab(SimpleVocabulary):

    def __init__(self, context):
        self.context = context
        values = [(i[0], i[1].description) for i in 
                  getUtilitiesFor(IExposureDocumentFactory)]
        # sort by description
        values.sort(cmp=lambda x, y: cmp(x[1], y[1]))
        terms = [SimpleTerm(*i) for i in values]
        super(PMR2ExposureDocumentFactoryVocab, self).__init__(terms)

# Someone please save me / I am becoming one of / those FactoryFactory
def PMR2ExposureDocumentFactoryVocabFactory(context):
    return PMR2ExposureDocumentFactoryVocab(context)

alsoProvides(PMR2ExposureDocumentFactoryVocabFactory, IVocabularyFactory)


