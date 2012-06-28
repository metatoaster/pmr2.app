from os.path import dirname
from os.path import join

import zope.component
from zope.component import testing
from Testing import ZopeTestCase as ztc
from Zope2.App import zcml
from Products.Five import fiveconfigure
from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import PloneSite
from Products.PloneTestCase.layer import onsetup
from Products.PloneTestCase.layer import onteardown

import pmr2.testing
from pmr2.testing import utils
from pmr2.app.workspace.tests.base import WorkspaceDocTestCase


@onsetup
def setup():
    import pmr2.app
    import pmr2.app.annotation.tests
    fiveconfigure.debug_mode = True
    zcml.load_config('configure.zcml', pmr2.app)
    zcml.load_config('test.zcml', pmr2.app.annotation.tests)
    zcml.load_config('test.zcml', pmr2.app.exposure.tests)
    fiveconfigure.debug_mode = False
    ztc.installPackage('pmr2.app')

@onteardown
def teardown():
    pass

setup()
teardown()
ptc.setupPloneSite(products=('pmr2.app',))


class ExposureDocTestCase(WorkspaceDocTestCase):

    def setUp(self):
        """\
        Sets up the environment that the exposure doctest needs.
        """

        super(ExposureDocTestCase, self).setUp()

        self.pmr2.default_exposure_idgen = 'rand128hex'
        self.pmr2.repo_root = self.tmpdir

        from pmr2.app.workspace.content import WorkspaceContainer, Workspace

        self.portal['workspace'] = WorkspaceContainer()
        def mkdummywks(name):
            w = Workspace(name)
            w.storage = 'dummy_storage'
            self.portal.workspace[name] = w

        mkdummywks('test')
        mkdummywks('cake')

        # unassigned
        self.portal.workspace['blank'] = Workspace('blank')

        # legacy test case.
        self.portal.workspace['eggs'] = Workspace('eggs')
        utils.mkreporoot(self.pmr2.createDir(self.portal))
        utils.mkrepo(self.pmr2.dirOf(self.portal.workspace.eggs))


class CompleteDocTestCase(ExposureDocTestCase):

    def setUp(self):
        """\
        Completes the other data within the portal so that other test
        classes don't have to set up Exposure objects and friends.
        """

        super(CompleteDocTestCase, self).setUp()

        from pmr2.app.settings.interfaces import IPMR2GlobalSettings
        from pmr2.idgen.interfaces import IIdGenerator
        from pmr2.app.workspace.content import Workspace
        from pmr2.app.exposure.content import ExposureContainer, Exposure

        settings = zope.component.queryUtility(IPMR2GlobalSettings)
        idgen = zope.component.queryUtility(IIdGenerator,
            name=settings.default_exposure_idgen)

        self.portal['exposure'] = ExposureContainer()
        def mkexposure(workspace, commit_id, id_):
            if not id_:
                id_ = idgen.next()
            else:
                # call it anyway.
                idgen.next()
            e = Exposure(id_)
            e.workspace = workspace
            e.commit_id = commit_id
            self.portal.exposure[id_] = e
            self.portal.exposure[id_].reindexObject()

        mkexposure(u'/plone/workspace/test', u'2', '1')
        mkexposure(u'/plone/workspace/eggs', u'1', '2')
