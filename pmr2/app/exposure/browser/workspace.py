import json

import zope.component
import zope.interface
from zope.publisher.interfaces import NotFound
from zope.publisher.interfaces.browser import IBrowserRequest

from zope.i18nmessageid import MessageFactory
_ = MessageFactory("pmr2")

import z3c.form
from plone.z3cform.fieldsets import group, extensible

from Acquisition import aq_inner, aq_parent
from AccessControl import Unauthorized
from Products.CMFCore.utils import getToolByName
from Products.statusmessages.interfaces import IStatusMessage

from pmr2.z3cform import form
from pmr2.z3cform import page

from pmr2.app.workspace.interfaces import IStorage, IWorkspace
from pmr2.app.workspace.interfaces import ICurrentCommitIdProvider
from pmr2.app.workspace.exceptions import *
from pmr2.app.workspace.browser.browser import WorkspaceLog

from pmr2.app.interfaces import *
from pmr2.app.interfaces.exceptions import *
from pmr2.app.annotation.interfaces import *
from pmr2.app.exposure.content import *

from pmr2.app.exposure import table
from pmr2.app.exposure.interfaces import *
from pmr2.app.exposure.browser.interfaces import *
from pmr2.app.exposure.browser.util import *
from pmr2.app.exposure.urlopen import urlopen
from pmr2.app.exposure.browser.browser import ViewPageTemplateFile
from pmr2.app.exposure.browser.browser import ExposurePort, ExposureAddForm


class ParentCurrentCommitIdProvider(object):
    """\
    Parent commit id provider mixin.
    """

    zope.interface.implements(ICurrentCommitIdProvider)

    def current_commit_id(self):
        parent = aq_parent(aq_inner(self))
        if ICurrentCommitIdProvider.providedBy(parent):
            return parent.current_commit_id()


class ExtensibleAddForm(form.AddForm, extensible.ExtensibleForm):

    _createdAndAdded = None

    def __init__(self, *a, **kw):
        super(ExtensibleAddForm, self).__init__(*a, **kw)
        self.groups = []
        self.fields = z3c.form.field.Fields()

    def update(self):
        extensible.ExtensibleForm.update(self)
        form.AddForm.update(self)

    def createAndAdd(self, data):
        if self._createdAndAdded:
            return self._createdAndAdded
        obj = super(ExtensibleAddForm, self).createAndAdd(data)
        self._createdAndAdded = obj
        return obj


class CreateExposureForm(ExtensibleAddForm, page.TraversePage):
    """\
    Page that will create an exposure inside the default exposure
    container from within a workspace.
    """

    zope.interface.implements(ICreateExposureForm, ICurrentCommitIdProvider)

    label = u"Exposure Creation Wizard"
    description = u"Please fill out the options for only one of the " \
                   "following sets of fields below to begin the exposure " \
                   "creation process."
    _gotExposureContainer = False

    def current_commit_id(self):
        commit_id = unicode(self.traverse_subpath[0])
        return commit_id

    def createAndAdd(self, data):
        obj = super(CreateExposureForm, self).createAndAdd(data)
        self.processGroups()
        return obj

    def create(self, data):
        # no data assignments here
        self._data = data
        generator = getGenerator(self)
        eid = generator.next()
        return Exposure(eid)

    def add(self, obj):
        """\
        The generic add method.
        """
        if not self.traverse_subpath:
            raise NotFound(self.context, self.context.title_or_id())

        exposure = obj
        workspace = u'/'.join(self.context.getPhysicalPath())
        commit_id = self.current_commit_id()

        try:
            exposure_container = restrictedGetExposureContainer()
        except Unauthorized:
            self.status = 'Unauthorized to create new exposure.'
            raise z3c.form.interfaces.ActionExecutionError(
                ExposureContainerInaccessibleError())
        self._gotExposureContainer = True

        exposure_container[exposure.id] = exposure
        exposure = exposure_container[exposure.id]
        exposure.workspace = workspace
        exposure.commit_id = commit_id
        exposure.setTitle(self.context.title)
        exposure.notifyWorkflowCreated()
        exposure.reindexObject()

        self.ctxobj = exposure

    def nextURL(self):
        return self.ctxobj.absolute_url() + '/@@wizard'

    def processGroups(self):
        """\
        Process groups that are here.
        """

        for g in self.groups:
            structure = g.acquireStructure()
            wh = zope.component.getAdapter(self.ctxobj, 
                IExposureWizard)
            if structure:
                wh.structure = structure
                break

    def render(self):
        if not self._gotExposureContainer:
            # we didn't finish.
            self._finishedAdd = False
        return super(CreateExposureForm, self).render()

    def __call__(self, *a, **kw):
        if not self.traverse_subpath:
            raise NotFound(self.context, self.context.title_or_id())

        try:
            storage = zope.component.getAdapter(self.context, IStorage)
            commit_id = unicode(self.traverse_subpath[0])
            # Make sure this is a valid revision.
            storage.checkout(commit_id)
        except (PathInvalidError, RevisionNotFoundError,):
            raise NotFound(self.context, commit_id)

        return super(CreateExposureForm, self).__call__(*a, **kw)


class CreateExposureGroupBase(form.Group, ParentCurrentCommitIdProvider):
    """\
    Base group for extending the exposure creator.
    """

    zope.interface.implements(ICreateExposureGroup)

    ignoreContext = True
    order = 0

    def acquireStructure(self):
        """\
        """

        raise NotImplementedError


class DocGenSubgroup(form.Group, ParentCurrentCommitIdProvider):
    """\
    Subgroup for docgen.
    """

    ignoreContext = True
    # this is to identify the marker to apply to the dummy object that
    # wraps around the actual structure.
    field_iface = None

    def generateStructure(self):
        raise NotImplementedError


class ExposureViewGenGroup(DocGenSubgroup):
    """\
    Subgroup for the view generator for Exposure and ExposureFolder.
    """

    zope.interface.implements(IExposureViewGenGroup)
    field_iface = IExposureViewGenGroup
    fields = z3c.form.field.Fields(IExposureViewGenGroup)
    prefix = 'view'
    filename = ''

    @property
    def label(self):
        if not self.filename:
            return 'Exposure main view'

        return 'Folder: %s' % self.filename

    def generateStructure(self):
        data, errors = self.extractData()
        if errors:
            return

        wks_path = None
        if IWorkspace.providedBy(self.context):
            wks_path = u'/'.join(self.context.getPhysicalPath())
        elif IExposure.providedBy(self.context):
            wks_path = self.context.workspace

        struct = {
            'docview_generator': data['docview_generator'],
            'docview_gensource': data['docview_gensource'],
            'Subject': (),  # XXX to be assigned by filetype?
        }

        if wks_path:
            struct.update({
                'commit_id': self.current_commit_id(),
                'curation': {},  # XXX no interface yet, and deprecated.
                'title': u'',  # XXX copy context?
                'workspace': wks_path,
            })

        structure = (self.filename, struct)

        return structure


class ExposureFileChoiceTypeGroup(DocGenSubgroup):
    """\
    Subgroup for the main exposure view generator.
    """

    label = 'New Exposure File Entry'
    field_iface = IExposureFileChoiceTypeGroup
    fields = z3c.form.field.Fields(IExposureFileChoiceTypeGroup)
    prefix = 'file'
    zope.interface.implements(IExposureFileChoiceTypeGroup)

    def generateStructure(self):
        data, errors = self.extractData()
        if errors:
            return

        if not (data['filename']):
            return

        result = getExposureFileType(self, data['filetype'])
        if result is None:
            # XXX might be better to raise an exception here as catalog
            # not found.
            return

        # Default items
        items = {
            'file_type': data['filetype'],
            'views': [],
            'selected_view': None,
            'Subject': (),
            # XXX additions for backwards compatibility.
            # 'docview_generator': None,
            # 'docview_gensource': None,
        }

        # we have what we want.
        title, views, tags, selected_view = result

        if views is not None:
            # update the structure with the indexed information of the
            # selected view.
            views = [(i, None) for i in views]
            items['views'] = views
            items['selected_view'] = selected_view
            items['Subject'] = tags

        structure = (data['filename'], items)
        return structure


class DocGenGroup(CreateExposureGroupBase):
    """\
    Group for the document generation.
    """

    label = "Standard exposure creator"
    description = "Please select the base file and/or the generation method."
    prefix = 'docgen'
    order = -10

    def update(self):
        # While adapters can be nice, the structure for this is rather
        # rigid at this point.  If adapters are to be included we will
        # have to rethink how this is to be integrated with the object
        # types that these groups represent.
        self.groups = []
        self.viewGroup = ExposureViewGenGroup(
            self.context, self.request, self)
        self.fileGroup = ExposureFileChoiceTypeGroup(
            self.context, self.request, self)
        self.groups.append(self.viewGroup)
        self.groups.append(self.fileGroup)

        return super(DocGenGroup, self).update()

    def acquireStructure(self):
        data, errors = self.extractData()
        if errors:
            # might need to notify the errors.
            return

        if not data['docview_generator'] and not data['filename']:
            # no root document and no filename to the first file.
            return

        structure = []
        if data['filename']:
            structure.append(self.fileGroup.generateStructure())
        structure.append(self.viewGroup.generateStructure())

        return structure


class ExposureImportExportGroup(CreateExposureGroupBase):
    """\
    Group for the document generation.
    """

    fields = z3c.form.field.Fields(IExposureExportImportGroup)
    label = "Exposure Import via URI"
    prefix = 'exportimport'

    def _loadExported(self, uri):
        u = urlopen(uri)
        exported = json.load(u)
        u.close()
        return exported

    def acquireStructure(self):
        data, errors = self.extractData()
        if errors:
            return

        uri = data.get('export_uri', None)
        if not uri:
            return

        try:
            result = self._loadExported(uri)
        except Exception, e:
            # can't pinpoint the right widget because the default error
            # handling subscriber will try to find `export_uri` in the 
            # parentForm and not this one.

            # raise z3c.form.interfaces.WidgetActionExecutionError(
            #     'export_uri', e)o
            
            # So we raise a normal one instead.
            raise z3c.form.interfaces.ActionExecutionError(
                ProcessingError(str(e)))

        return result


class CreateExposureFormExtender(extensible.FormExtender):
    zope.component.adapts(
        IWorkspace, IBrowserRequest, ICreateExposureForm)

    def update(self):
        # Collect all the groups, instantiate them, add them to parent.
        groups = zope.component.getAdapters(
            (self.context, self.request, self.form),
            ICreateExposureGroup,
        )
        for k, g in sorted(groups, key=extensible.order_key):
            self.add(g)

    def add(self, group):
        self.form.groups.append(group)


class WorkspaceExposureRollover(ExposurePort, WorkspaceLog):

    # more suitable interface name needed?
    zope.interface.implements(IExposureRolloverForm)
    _finishedAdd = False
    fields = z3c.form.field.Fields(IExposureRolloverForm)
    label = 'Exposure Rollover'

    shortlog = True
    tbl = table.ExposureRolloverLogTable
    template = ViewPageTemplateFile('workspace_exposure_rollover.pt')

    def update(self):
        self.request['enable_border'] = True
        ExposurePort.update(self)
        WorkspaceLog.update(self)

    def export_source(self):
        return self.source_exposure

    # acquire default container
    def getDefaultExposureContainer(self):
        try:
            exposure_container = restrictedGetExposureContainer()
            self._gotExposureContainer = True
        except:
            raise ProcessingError(
                u'Unauthorized to create new exposure at default location.')
        return exposure_container

    def acquireSource(self, exposure_path):
        try:
            source_exposure = self.context.restrictedTraverse(
               exposure_path)
        except Unauthorized:
            raise ProcessingError(
                u'Unauthorized to read exposure at selected location')
        except (AttributeError, KeyError):
            raise ProcessingError(
                u'Cannot find exposure at selected location.')
        return source_exposure

    @z3c.form.button.buttonAndHandler(_('Migrate'), name='apply')
    def handleMigrate(self, action):
        data, errors = self.extractData()
        if errors:
            status = IStatusMessage(self.request)
            status.addStatusMessage(
                u'Please ensure both radio columns have been selected before '
                 'trying again.',
                'error')
            return

        try:
            exposure_container = self.getDefaultExposureContainer()
            self.source_exposure = self.acquireSource(data['exposure_path'])
        except ProcessingError, e:
            raise z3c.form.interfaces.ActionExecutionError(e)

        eaf = ExposureAddForm(exposure_container, None)
        data = {
            'workspace': u'/'.join(self.context.getPhysicalPath()),
            'curation': None,  # deprecated?
            'commit_id': data['commit_id'],
        }
        eaf.createAndAdd(data)
        exp_id = data['id']
        target = exposure_container[exp_id]

        exported = self.export()
        wh = zope.component.getAdapter(target, IExposureWizard)
        wh.structure = list(exported)

        self._finishedAdd = True
        self.target = target

    def nextURL(self):
        return self.target.absolute_url() + '/@@wizard'

    def render(self):
        if self._finishedAdd:
            self.request.response.redirect(self.nextURL())
            return ""
        return super(WorkspaceExposureRollover, self).render()
