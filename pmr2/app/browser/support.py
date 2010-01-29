import zope.component
from paste.httpexceptions import HTTPNotFound

import z3c.form.field
import z3c.form.form

from plone.z3cform import layout

from pmr2.app.browser.interfaces import IPMR2SearchAdd
from pmr2.app.content.interfaces import IPMR2Search
from pmr2.app.content import PMR2Search

from Products.CMFCore.utils import getToolByName

from pmr2.app.browser import form
from pmr2.app.browser import page
from pmr2.app.browser.layout import BorderedTraverseFormWrapper


class PMR2SearchAddForm(form.AddForm):
    """\
    Repository root add form.
    """

    fields = z3c.form.field.Fields(IPMR2SearchAdd).select(
        'id',
        'title',
        'description',
        'catalog_index',
    )
    clsobj = PMR2Search

    # XXX register this as fti factory so the URI of this obj will be
    # used instead of createObject from the Plone menu
    # see: plone.app.contentmenu/plone/app/contentmenu/menu.py:709

    def add_data(self, ctxobj):
        #ctxobj.title = self._data['title']
        #ctxobj.description = self._data['description']
        ctxobj.catalog_index = self._data['catalog_index']

PMR2SearchAddFormView = layout.wrap_form(PMR2SearchAddForm,
    label="PMR2 Custom Search Add Form")


class PMR2SearchEditForm(form.EditForm):
    """\
    Repository Edit/Management Form.
    """

    fields = z3c.form.field.Fields(IPMR2Search)

PMR2SearchEditFormView = layout.wrap_form(
    PMR2SearchEditForm, label="Repository Management")


class PMR2SearchPage(page.TraversePage):
    """\
    Wraps an object around the mathml view.
    """

    filetemplate = page.ViewPageTemplateFile('pmr2search.pt')

    def __call__(self, *args, **kwargs):

        def clean_searchterm():
            if not hasattr(self, 'searchterm') or self.searchterm is None:
                self.searchterm = None
                return False
            self.searchterm = self.searchterm.replace(' ', '_')
            return True

        def build_saved_searches():
            q = {
                'query': '/'.join(self.context.getPhysicalPath()),
                'navtree': 0,
                'depth': 1,
            }
            self.saved_searches = pt(path=q)

        def build_results():
            d = {}
            d[self.context.catalog_index] = self.searchterm
            self.all_results = pt(**d)
            if not self.all_results:
                raise HTTPNotFound(self.context.title_or_id())

        def build_terms():
            try:
                self.all_terms = \
                    pt.Indexes[self.context.catalog_index].uniqueValues()
            except NotImplementedError:
                pass

        pt = getToolByName(self.context, 'portal_catalog')
        if self.context.catalog_index not in pt.Indexes:
            # Nothing is set.
            return

        self.catalog_index = self.context.catalog_index
        self.searchterm = None
        if 'request_subpath' in self.request:
            self.searchterm = '/'.join(self.request['request_subpath'])

        # now call the methods to set the variables for the template.
        if clean_searchterm():
            build_results()
        else:
            build_saved_searches()
            # XXX remove items that are saved?
            build_terms()
        return self.filetemplate()

PMR2SearchPageView = layout.wrap_form(
    PMR2SearchPage,
    __wrapper_class=BorderedTraverseFormWrapper,
)
