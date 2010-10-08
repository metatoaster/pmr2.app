import warnings
import mimetypes
import urllib

import zope.interface
import zope.component
import zope.event
import zope.lifecycleevent
import zope.publisher.browser
from zope.i18nmessageid import MessageFactory
_ = MessageFactory("pmr2")

from paste.httpexceptions import HTTPNotFound, HTTPFound

import z3c.form.interfaces
import z3c.form.field
import z3c.form.form
import z3c.form.value
import z3c.form.button

from plone.z3cform import layout
from Products.CMFCore.utils import getToolByName
from Acquisition import aq_parent, aq_inner

import pmr2.mercurial.exceptions
import pmr2.mercurial.utils
from pmr2.mercurial import Storage

from pmr2.app.interfaces import *
from pmr2.app.interfaces import IPMR2GlobalSettings
from pmr2.app.workspace.interfaces import *
from pmr2.app.workspace.content import *
from pmr2.app.util import set_xmlbase, obfuscate, isodate

from pmr2.app.browser import interfaces
from pmr2.app.browser import widget
from pmr2.app.browser import form
from pmr2.app.browser import page
from pmr2.app.browser.page import ViewPageTemplateFile

from pmr2.app.browser.layout import BorderedStorageFormWrapper
from pmr2.app.browser.layout import BorderedTraverseFormWrapper
from pmr2.app.browser.layout import TraverseFormWrapper

from pmr2.app.workspace.interfaces import *
from pmr2.app.workspace import table


# Workspace Container

class WorkspaceContainerAddForm(form.AddForm):
    """\
    Workspace container add form.
    """

    fields = z3c.form.field.Fields(IWorkspaceContainer).select(
        'title',
    )
    clsobj = WorkspaceContainer

    def add_data(self, ctxobj):
        ctxobj.title = self._data['title']

WorkspaceContainerAddFormView = layout.wrap_form(
    WorkspaceContainerAddForm, label="Workspace Container Add Form")


class WorkspaceContainerEditForm(form.EditForm):
    """\
    Workspace Container Edit form
    """

    fields = z3c.form.field.Fields(IWorkspaceContainer).select(
        'title',
    )

WorkspaceContainerEditFormView = layout.wrap_form(
    WorkspaceContainerEditForm, label="Workspace Container Management")


class WorkspaceContainerRepoListing(page.SimplePage):

    def content(self):
        t = table.WorkspaceStatusTable(self.context, self.request)
        # XXX no idea why this isn't done automatically
        t.__name__ = self.__name__
        try:
            t.update()
            # need styling the first, current and last class of renderBatch
            return '\n'.join([t.render(), t.renderBatch()])
        except PathLookupError:
            return u'<div class="error">Repository Path lookup failed.</div>'
        except RepoPathUndefinedError:
            # this may be made obsolete by the previous error.
            return u'<div class="error">Repository Path is undefined.</div>'
        except WorkspaceDirNotExistsError:
            return u'<div class="error">Workspace path is missing. ' \
                    'Please notify administrator.</div>'


WorkspaceContainerRepoListingView = layout.wrap_form(
    WorkspaceContainerRepoListing, label="Raw Workspace Listing")


# Workspace

class WorkspaceProtocol(zope.publisher.browser.BrowserPage):
    """\
    Browser page that encapsulates access to the Mercurial protocol.
    """

    # XXX this class is currently unused until the permissions can be
    # totally handled "correctly".

    def __call__(self, *a, **kw):
        try:
            storage = getMultiAdapter((self.context,), name='PMR2Storage')
        except pmr2.mercurial.exceptions.PathInvalidError:
            # This is raised in the case where a Workspace object exists
            # without a corresponding Hg repo on the filesystem.
            # XXX should be raising NotFound instead of some other error 
            # page that accurately describe this error.
            raise HTTPNotFound(self.context.title_or_id())

        try:
            # Process the request.
            return storage.process_request(self.request)
        except pmr2.mercurial.exceptions.UnsupportedCommandError:
            # Can't do this command, redirect back to root object.
            raise HTTPFound(self.context.absolute_url())


class WorkspaceArchive(page.TraversePage):
    """\
    Browser page that archives a hg repo.
    """

    def __call__(self, *a, **kw):
        try:
            storage = zope.component.queryMultiAdapter(
                (self.context, self.request, self), 
                name="PMR2StorageRequestView",
            )
        except (pmr2.mercurial.exceptions.PathInvalidError,
                pmr2.mercurial.exceptions.RevisionNotFoundError,
            ):
            raise HTTPNotFound(self.context.title_or_id())

        subrepo = self.request.form.get('subrepo', False)
        return storage.archive(subrepo).getvalue()


class WorkspacePage(page.SimplePage):
    """\
    The main page view.
    """
    # XXX the implementation works, but is probably not best practice
    # way to implement views based on other classes.

    template = ViewPageTemplateFile('workspace.pt')

    @property
    def owner(self):
        if not hasattr(self, '_owner'):
            owner = self.context.getOwner()
            result = '%s <%s>' % (
                owner.getProperty('fullname', owner.getId()),
                owner.getProperty('email', ''),
            )
            self._owner = obfuscate(result)

        return self._owner

    def shortlog(self):
        if not hasattr(self, '_log'):
            # XXX aq_inner(self.context) not needed?
            self._log = WorkspaceShortlog(self.context, self.request)
            # set our requirements.
            self._log.maxchanges = 10  # XXX magic number
            self._log.navlist = None
        return self._log()


WorkspacePageView = layout.wrap_form(
    WorkspacePage,
    __wrapper_class=BorderedStorageFormWrapper,
)


class WorkspaceLog(page.NavPage, z3c.table.value.ValuesForContainer):

    zope.interface.implements(IWorkspaceLogProvider)

    # XXX no this does not work
    # XXX need to hack context_fti or DynamicViewTypeInformation somehow
    # to make it do what needs to be done.
    # This value could be captured using DynamicViewTypeInformation
    # XXX this needs to be fixed to take advantage of shared adapted result.
    shortlog = False
    tbl = table.ChangelogTable
    maxchanges = None  # default value.
    datefmt = None # default value.

    @property
    def log(self):
        if not hasattr(self, '_log'):
            try:
                storage = zope.component.queryMultiAdapter(
                    (self.context, self.request, self), 
                    name="PMR2StorageRequestView",
                )
                self._log = storage.get_log(shortlog=self.shortlog,
                                            datefmt=self.datefmt,
                                            maxchanges=self.maxchanges)
            except pmr2.mercurial.exceptions.RevisionNotFoundError:
                raise HTTPNotFound(self.context.title_or_id())
        return self._log

    def navlist(self):
        # XXX we are merging before/after together.
        nav = self.log['changenav'][0]
        for i in nav['before']():
            yield {
                'href': i['node'],
                'label': i['label'],
            }
        for i in nav['after']():
            yield {
                'href': i['node'],
                'label': i['label'],
            }

    @property
    def values(self):
        """\
        Although this is a property, it will return a method that 
        returns a generator.
        """

        return self.log['entries']

    def content(self):
        t = self.tbl(self, self.request)
        t.update()
        return t.render()

WorkspaceLogView = layout.wrap_form(
    WorkspaceLog, 
    __wrapper_class=BorderedTraverseFormWrapper,
    label='Changelog Entries'
)


class WorkspaceShortlog(WorkspaceLog):

    shortlog = True
    tbl = table.ShortlogTable

WorkspaceShortlogView = layout.wrap_form(
    WorkspaceShortlog,
    __wrapper_class=BorderedTraverseFormWrapper,
    label='Shortlog'
)


#class WorkspacePageShortlog(WorkspaceShortlog):
#    # for workspace main listing.
#
#    tbl = table.WorkspacePageShortlogTable
#

class WorkspaceLogRss(page.RssPage, WorkspaceLog):

    datefmt = 'rfc822date'

    def items(self):
        for i in self.values():
            yield {
                'title': i['desc'].splitlines()[0],
                # XXX magic manifest link
                'link': '%s/@@file/%s' % (
                    self.context.context.absolute_url(),
                    i['node'],
                ),
                'description': i['desc'],
                'author': obfuscate(i['author']),
                'pubDate': i['date'],
            }


class WorkspaceAddForm(form.AddForm):
    """\
    Workspace add form.
    """

    fields = z3c.form.field.Fields(interfaces.IObjectIdMixin) + \
             z3c.form.field.Fields(IWorkspace)
    clsobj = Workspace

    def add_data(self, ctxobj):
        ctxobj.title = self._data['title']
        ctxobj.description = self._data['description']

WorkspaceAddFormView = layout.wrap_form(
    WorkspaceAddForm, label="Workspace Object Creation Form")


class WorkspaceStorageCreateForm(WorkspaceAddForm):
    """\
    Workspace add form.  This also creates the storage object.
    """

    # IWorkspaceStorageCreate has a validator attached to its id 
    # attribute to verify that the workspace id has not been taken yet.
    fields = z3c.form.field.Fields(IWorkspaceStorageCreate) + \
             z3c.form.field.Fields(IWorkspace)

    def add_data(self, ctxobj):
        WorkspaceAddForm.add_data(self, ctxobj)
        # path shouldn't exist, but don't make it
        rp = zope.component.getUtility(IPMR2GlobalSettings).dirOf(ctxobj)
        # This creates the mercurial workspace, and will fail if storage
        # already exists.
        Storage.create(rp, ffa=True)

WorkspaceStorageCreateFormView = layout.wrap_form(
    WorkspaceStorageCreateForm, label="Create a New Workspace")


class WorkspaceBulkAddForm(z3c.form.form.AddForm):
    """\
    Workspace Bulk Add Form
    """

    fields = z3c.form.field.Fields(IWorkspaceBulkAdd)

    result_base = """\
      <dt>%s</dt>
      <dd>%d</dd>
    """

    failure_base = """
      <dt>%s</dt>
      <dd>
      <ul>
      %s
      </ul>
      </dd>
    """

    def completed(self):
        result = ['<p>The results of the bulk import:</p>', '<dl>']
        if self.created:
            result.append(self.result_base % ('Success', self.created))
        if self.existed:
            result.append(self.result_base % ('Existed', self.existed))
        if self.norepo:
            result.append(self.failure_base % ('Mercurial Repo Not Found',
            '\n'.join(['<li>%s</li>' % i for i in self.norepo]))
        )
        if self.failed:
            result.append(self.failure_base % ('Other Failure',
            '\n'.join(['<li>%s</li>' % i for i in self.failed]))
        )
        result.append('</dl>')
        return '\n'.join(result)

    def createAndAdd(self, data):
        self.created = self.existed = 0
        self.failed = []
        self.norepo = []

        workspaces = data['workspace_list'].splitlines()
        listing = zope.component.getAdapter(self.context, IWorkspaceListing)
        valid_hg = [i[0] for i in listing()]
        for id_ in workspaces:
            # unicode encoding needed here?
            id_ = str(id_)  # id_.encode('utf8')
            if not id_:
                continue
            if id_ not in valid_hg:
                # Only repo not found are reported as failures.
                self.norepo.append(id_)
                continue
            if id_ in self.context:
                self.existed += 1
                continue

            try:
                obj = Workspace(id_, **data)
                zope.event.notify(zope.lifecycleevent.ObjectCreatedEvent(obj))
                self.context[id_] = obj
                obj = self.context[id_]
                obj.title = id_.replace('_', ', ').title()
                obj.notifyWorkflowCreated()
                obj.reindexObject()
                self.created += 1
            except:
                # log stacktrace?
                self.failed.append(id_)

        # marking this as done.
        self._finishedAdd = True

    def nextURL(self):
        """\
        Go back to the Workspace Container
        """

        return self.context.absolute_url()

    def render(self):
        if self._finishedAdd:
            return self.completed()
        return super(WorkspaceBulkAddForm, self).render()

WorkspaceBulkAddFormView = layout.wrap_form(
    WorkspaceBulkAddForm, label="Workspace Bulk Creation Form")


class WorkspaceEditForm(form.EditForm):
    """\
    Workspace edit form.
    """

    fields = z3c.form.field.Fields(IWorkspace)

WorkspaceEditFormView = layout.wrap_form(
    WorkspaceEditForm, label="Workspace Edit Form")


class WorkspaceFilePage(page.TraversePage, z3c.table.value.ValuesForContainer):
    """\
    Manifest listing page.
    """
    
    zope.interface.implements(IWorkspaceFilePageView, 
        IWorkspaceLogProvider,
        IWorkspaceFileListProvider,
        interfaces.IUpdatablePageView)

    template = ViewPageTemplateFile('workspace_file_page.pt')
    filetemplate = ViewPageTemplateFile('file.pt')

    def __init__(self, *a, **kw):
        super(WorkspaceFilePage, self).__init__(*a, **kw)
        self.manifest = self.fileinfo = None

    # XXX overriding traverse subpath here to define additional behavior
    def publishTraverse(self, request, name):
        self.traverse_subpath.append(name)
        if self.request.get('rev', None) is None:
            self.request['rev'] = name
            self.request['request_subpath'] = []
        else:
            self.request['request_subpath'].append(name)
        return self

    def update(self):
        """
        Populate internal data structures.
        """

        # it may be desirable if the 404 pages return something more
        # meaningful.
        try:
            self._structure = self.storage.structure
        except pmr2.mercurial.exceptions.RevisionNotFoundError:
            raise HTTPNotFound(self.context.title_or_id())
        except pmr2.mercurial.exceptions.PathNotFoundError:
            raise HTTPNotFound(self.context.title_or_id())
        except pmr2.mercurial.exceptions.RepoEmptyError:
            # Since repository empty, we return an empty structure.
            self._structure = {}
            return

        if self._structure[''] == 'filerevision':
            self.fileinfo = self._structure
            # XXX should figure out how to set date format in structure
            # rather than rebuilding
            self.fileinfo['date'] = isodate(self.fileinfo['date'])
        elif self._structure[''] == 'manifest':
            self.manifest = self._structure
            # XXX hacks, because this class is trying to render more
            # than one data source.
            self.render_subrepo = True
        elif self._structure[''] == '_subrepo':
            uri = '%s/@@%s/%s/%s' % (
                self._structure['location'],
                self.__name__,
                self._structure['rev'],
                self._structure['path'],
            )
            raise HTTPFound(uri)
        else:
            # not sure what to do
            raise Exception("unknown storage response structure")

    @property
    def storage(self):
        # XXX placeholder
        self.request.form['cmd'] = ['file']
        if not hasattr(self, '_storage'):
            self._storage = zope.component.queryMultiAdapter(
                (self.context, self.request, self),
                name="PMR2StorageRequestView"
            )
        return self._storage

    @property
    def structure(self):
        if hasattr(self, '_structure'):
            return self._structure

    # XXX rewrite this class to use adapters for specific views for 
    # these distinct types of values
    @property
    def values(self):
        """
        provides values for the table.
        """

        if self.structure[''] == 'filerevision':
            return self.fileinfo['text']
        elif self.structure[''] == 'manifest':
            return self.manifest['aentries']
        return []

    def content(self):

        if self.structure is None:
            raise HTTPNotFound(self.context.title_or_id())

        if self.structure[''] == 'manifest':
            t = table.FileManifestTable(self, self.request)
            t.update()
            return t.render()
        else:
            return self.filetemplate()

    @property
    def label(self):
        """
        provides values for the form.
        """

        if not self.structure:
            return u''

        if self.structure[''] == 'filerevision':
            label = 'Fileinfo'
        elif self.structure[''] == 'manifest':
            label = 'Manifest'
        else:
            return u'No Information Available'
        rev = self.storage.rev
        if rev:
            rev = rev[:10]
        else:
            # emulating null ID.
            rev = '0' * 10
        return u'%s: %s @ %s / %s' % (
            label, self.context.title_or_id(), rev,
            self.storage.path.replace('/', ' / '),
        )

    def _getpath(self, view='rawfile', path=None):
        result = [
            self.context.absolute_url(),
            '@@' + view,
            self.storage.rev,
        ]
        if path:
            result.append(path)
        return result

    @property
    def rooturi(self):
        """the root uri."""
        return '/'.join(self._getpath())

    @property
    def xmlrooturi(self):
        """the root uri."""
        return '/'.join(self._getpath(view='xmlbase'))

    @property
    def fullpath(self):
        """permanent uri."""
        return '/'.join(self._getpath(path=self.storage.path))

    @property
    def viewpath(self):
        """view uri."""
        return '/'.join(self._getpath(view='file', path=self.storage.path))

    @property
    def subrepo(self):
        # XXX directly using internals?
        try:
            substate = self.storage.ctx.substate
        except:
            # XXX catchall
            return []
        result = []
        for location, subrepo in substate.iteritems():
            source, rev, kind = subrepo
            result.append((location, source, rev))
        result.sort()
        result = [dict(zip(('location', 'source', 'rev'), i)) for i in result]
        return result

WorkspaceFilePageView = layout.wrap_form(
    WorkspaceFilePage,
    __wrapper_class=BorderedTraverseFormWrapper,
)
# XXX WorkspaceFilePageView needs to implement
#zope.interface.implements(IWorkspaceFilePageView)


class WorkspaceRawfileView(WorkspaceFilePage):

    def __call__(self):
        self.update()
        if self.structure:
            # not supporting resuming download
            # XXX large files will eat RAM
            try:
                data = self.storage.rawfile
            except pmr2.mercurial.exceptions.PathNotFoundError:
                # this is a rawfile view, this can be triggered by 
                # attempting to access a directory.  we redirect to the
                # standard file view.
                raise HTTPFound(self.viewpath)
            mt = mimetypes.guess_type(self.storage.path)[0]
            if mt is None or (data and '\0' in data[:4096]):
                mt = mt or 'application/octet-stream'
            self.request.response.setHeader('Content-Type', mt)
            self.request.response.setHeader('Content-Length', len(data))
            return data
        else:
            raise HTTPNotFound(self.context.title_or_id())


class WorkspaceRawfileXmlBaseView(WorkspaceRawfileView):

    def find_type(self):
        # XXX should really hook into mimetype registry and not hard
        # coded in here.
        if self.storage.path.endswith('session.xml'):
            return 'application/x-pcenv-cellml+xml'
        elif self.storage.path.endswith('.cellml'):
            return 'application/cellml+xml'

    def __call__(self):
        data = WorkspaceRawfileView.__call__(self)
        frag = self.storage.path.rsplit('/', 1)
        filename = frag.pop()
        s_path = frag and frag.pop() or ''

        # add the xml:base, with empty end string for trailing /
        # since this is the xml base rewrite, we be consistent.
        xmlroot = '/'.join((self.xmlrooturi, s_path, '',))
        data = set_xmlbase(data, xmlroot)

        # all done, now set headers.
        contentType = self.find_type()
        if contentType:
            self.request.response.setHeader('Content-Type', contentType)
        self.request.response.setHeader('Content-Disposition',
            'attachment; filename="%s"' % filename,
        )
        self.request.response.setHeader('Content-Length', len(data))

        return data