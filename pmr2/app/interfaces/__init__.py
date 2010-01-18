import zope.schema
import zope.interface

from zope.i18nmessageid import MessageFactory
_ = MessageFactory("pmr2")

from pmr2.app.schema import ObjectId, WorkspaceList, CurationDict, TextLineList


# FIXME I am HUEG.

# General exceptions.

class PathLookupError(LookupError):
    """cannot calculate the path to some resource.."""


# Validation errors

class ObjectIdExistsError(zope.schema.ValidationError):
    __doc__ = _("""The specified id is already in use.""")


class StorageExistsError(zope.schema.ValidationError):
    __doc__ = _("""A previous workspace may have used this id but is not fully removed from the system.  Please use another id.""")


class InvalidPathError(zope.schema.ValidationError):
    __doc__ = _("""The value specified is not a valid path.""")


class RepoRootNotExistsError(zope.schema.ValidationError):
    __doc__ = _("""The repository root at the specified path does not exist.""")


class RepoNotExistsError(zope.schema.ValidationError):
    __doc__ = _("""The repository at the specified path does not exist.""")


class RepoPathUndefinedError(zope.schema.ValidationError):
    __doc__ = _("""The repository path is undefined.""")


class WorkspaceDirNotExistsError(zope.schema.ValidationError):
    __doc__ = _("""The workspace directory does not exist.""")


class WorkspaceObjNotFoundError(zope.schema.ValidationError):
    __doc__ = _("""The workspace object is not found.""")


# Interfaces

class IObjectIdMixin(zope.interface.Interface):
    """\
    For use by any interface that will be used by AddForm; this
    basically gives an 'id' field for the user to input.
    """

    id = ObjectId(
        title=u'Id',
        description=u'The identifier of the object, used for URI.',
    )


class IPMR2(zope.interface.Interface):
    """\
    Interface for the root container for the entire model repository.
    """

    title = zope.schema.TextLine(
        title=u'Title',
        description=u'The title or name given to this repository.',
    )

    repo_root = zope.schema.BytesLine(
        title=u'Repository Path',
        description=u'The working directory of this repository. This '
                     'directory contains the raw VCS repositories of the '
                     'models.',
        readonly=False,
    )

    # workspace_path is 'workspace'
    # sandbox_path is 'sandbox'


class IPMR2Add(IObjectIdMixin, IPMR2):
    """\
    Interface for the use by PMR2AddForm.
    """


class IPMR2GetPath(zope.interface.Interface):
    """\
    Provides method to return a PMR2 related path on the filesystem
    based on some configured value.
    """

    def get_path():
        """\
        Returns the root directory where all the workspaces are stored.

        Need to raises PathLookupError if the path cannot be calculated.
        """


class IWorkspaceContainer(zope.interface.Interface):
    """\
    Container for the model workspaces.
    """

    title = zope.schema.TextLine(
        title=u'Title',
        default=u'Workspace',
    )

    get_repository_list, = zope.schema.accessors(WorkspaceList(
        title=u'Repository List',
        readonly=True,
    ))


class ISandboxContainer(zope.interface.Interface):
    """\
    Container for the sandboxes (working copies).
    """

    title = zope.schema.TextLine(
        title=u'Title',
        default=u'Sandbox',
    )


class IExposureContainer(zope.interface.Interface):
    """\
    Container for all exposure pages.
    """

    title = zope.schema.TextLine(
        title=u'Title',
        default=u'Exposure',
    )


class IWorkspace(zope.interface.Interface):
    """\
    Model workspace.
    """

    # id would be the actual path on filesystem

    title = zope.schema.TextLine(
        title=u'Title',
        required=False,
    )

    description = zope.schema.Text(
        title=u'Description',
        required=False,
    )


class IWorkspaceAdd(IObjectIdMixin, IWorkspace):
    """\
    Interface for the use by WorkspaceAddForm.
    """


class IWorkspaceStorageCreate(IWorkspaceAdd):
    """\
    Interface for the use by WorkspaceStorageCreateForm.
    """

    # We customized the id so validator can discrimate this against
    # the generate mixin id field.
    id = ObjectId(
        title=u'Id',
        description=u'The identifier of the object, used for URI.',
    )


class IWorkspaceBulkAdd(zope.interface.Interface):
    """\
    Interface for the use by WorkspaceAddForm.
    """

    workspace_list = zope.schema.Text(
        title=u'List of Workspaces',
        description=u'List of Mercurial Repositories created by pmr2_mkhg ' \
                     'that are already moved into the workspace directory.',
        required=True,
    )


class ISandbox(zope.interface.Interface):
    """\
    Container for the sandboxes (working copies).
    """

    title = zope.schema.TextLine(
        title=u'Title',
    )

    description = zope.schema.Text(
        title=u'Description',
    )

    status = zope.schema.Text(
        title=u'Status Messages',
        description=u'Status output from VCS',
    )


class IExposureObject(zope.interface.Interface):
    """\
    Any object within an exposure need to implement this.
    """


class IExposure(zope.interface.Interface):
    """\
    Container for all exposure pages.
    """

    title = zope.schema.TextLine(
        title=u'Title',
        required=False,
    )

    workspace = zope.schema.TextLine(
        title=u'Workspace',
        description=u'The model workspace this exposure encapsulates.',
    )

    commit_id = zope.schema.TextLine(
        title=u'Commit ID',
        description=u'The specific commit identifier of the model.',
    )

    curation = CurationDict(
        title=u'Curation',
        description=u'Curation of this model.',
        required=False,
    )

    # this is not a Choice because the manifest list generation can be
    # a performance hit as this object gets hit a lot, and we don't have
    # caching yet... not to mention users won't be changing this.
    docview_gensource = zope.schema.TextLine(
        title=u'Generated From',
        description=u'The source file which the documentation or data is '
                     'generated from.',
        required=False,
    )

    # sometimes generator can become depcrecated and removed, thus no
    # longer in the vocabulary, plain text field again.
    docview_generator = zope.schema.TextLine(
        title=u'Generator Name',
        description=u'The name of the generator used to make this view.',
        required=False,
    )


class IPMR2Search(zope.interface.Interface):
    """\
    Interface for the search objects.
    """

    title = zope.schema.TextLine(
        title=u'Title',
    )

    description = zope.schema.Text(
        title=u'Description',
        required=False,
    )

    catalog_index = zope.schema.Choice(
        title=u'Index',
        description=u'The index to be use by this search object.',
        vocabulary='PMR2IndexesVocab',
    )


class IPMR2SearchAdd(IObjectIdMixin, IPMR2Search):
    """\
    Interface for the use by PMR2AddForm.
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


class IExposureFolder(zope.interface.Interface):
    """\
    Interface for a folder within an exposure (supports unknwon subpath
    capturing for redirection to path within its workspace).
    """

    # for reason why these two fields are TextLine, please see IExposure
    docview_gensource = zope.schema.TextLine(
        title=u'Generated From',
        description=u'The source file which the documentation or data is '
                     'generated from.',
        required=False,
    )

    docview_generator = zope.schema.TextLine(
        title=u'Generator Name',
        description=u'The name of the generator used to make this view.',
        required=False,
    )


# New style exposure classes.

class IExposureFileGenForm(zope.interface.Interface):
    """\
    Interface for the form that will handle the generation of an
    ExposureFile object.
    """

    filename = zope.schema.Choice(
        title=u'File',
        description=u'The file within the workspace that requires special '\
                     'processing to be presentable in this exposure.',
        vocabulary='ManifestListVocab',
    )   # this will become the id of an ExposureFile object.


class IExposureFile(zope.interface.Interface):
    """\
    Interface for a basic exposure page.

    Compared to IExposureDocument, a lot less fields, because the object
    will have the id after the object.
    """

    views = TextLineList(
        title=u'Views',
        description=u'List of views available.',
        required=False,
        default=[],
    )

    docview_gensource = zope.schema.TextLine(
        title=u'Documentation File',
        description=u'The file where the documentation for this file reside '
                     'in, for files that do not have any method of specifying '
                     'one.',
        required=False,
    )

    docview_generator = zope.schema.TextLine(
        title=u'Default View Generator',
        description=u'The default view generator utility that was used to ' \
                     'generate the contents viewed via document_view.',
        required=False,
    )

    def raw_text():
        """\
        returns a concatenated string of all raw text, if it implements
        IExposureFileRawText
        """


class IExposureFileRawText(zope.interface.Interface):
    """\
    Interface that will allow the returning of raw text.
    """

    def raw_text():
        """\
        returns a raw text representation of this adapter.
        """


class IExposureFileAnnotator(zope.interface.Interface):
    """\
    Interface for the ExposureFile annotation utility.
    """

    # ef_note is the name/key of storage class to use

    title = zope.schema.Text(
        title=u'Title',
        description=u'Title of this annotator',
        required=False,
    )

    description = zope.schema.Text(
        title=u'Description',
        description=u'A brief note about what this annotator does.',
        required=False,
    )

    def generate(context):
        """\
        Process the input context to return a list of tuples in the
        form (name, value) where name is the name of the field for the
        respective note class to store the value in.
        """


class IExposureFileAnnotatorForm(zope.interface.Interface):
    """\
    Interface for the form and utility that that allows notes to be
    annotated to the ExposureFile.
    """

    annotators = zope.schema.Choice(
        title=u'Annotators Available',
        description=u'The selected annotators will annotate the current ' \
                     'file and enable the view.',
        vocabulary='ExposureFileAnnotatorVocab',
        required=True,
    )


class IExposureFileNoteEditForm(zope.interface.Interface):
    """\
    Interface for the note edit form.
    """

    # Lacking fields here because we don't have any fixed fields yet,
    # not to mention the fields are dynamically acquired from the name
    # of the note which is passed into via traversal subpath.


class IExposureFileViewUtility(zope.interface.Interface):
    """\
    Utilty for ExposureFile view classes.  Generally this will provide
    the data required for the rendering to happen.
    """

    # XXX if multiple annotations are used, one should create a subclass
    # which will form a new object, it will need to adapt...

    view = zope.schema.TextLine(
        title=u'View',
        description=u'The view that this view generator is design to enable.',
        required=True,
    )

    # provided by IExposureFileAnnotatorForm
    #annotators = zope.schema.List(
    #    title=u'Annotators',
    #    description=u'The annotators required by this view, identified by ' \
    #                 'the name it is registered under in the component ' \
    #                 'registry.',
    #    required=True,
    #)

    #def retrieve_from(context):
    #    """\
    #    Returns the data structure that will be used by the view.
    #    Normally this will return a context adapting the annotator in
    #    question.
    #    """

    #def generate(context):
    #    """\
    #    Sets the notes for this context.
    #    """


class IExposureFileNote(zope.interface.Interface):
    """\
    Interface for notes attached to ExposureFile objects.
    """


class IExposureFileEditableNote(zope.interface.Interface):
    """\
    Interface for notes attached to ExposureFile objects that are 
    editable by users.
    """


class IExposureFileView(zope.interface.Interface):
    """\
    Interface that will view an exposure file.  Usually they will need/
    acquire an ExposureFileNote object, and this is a marker itnerface
    that will assist in doing so.
    """


class IStandardExposureFile(zope.interface.Interface):
    """\
    An adapter that really isn't one, it just a marker to reuse the
    original context.
    """


class IRawTextNote(zope.interface.Interface):
    """\
    For an annotation adapter to the ExposureFile that will store raw
    text representation generated by its respective annotator.
    """

    text = zope.schema.Text(
        title=u'Text',
        required=False,
    )


class IGroupedNote(zope.interface.Interface):
    """\
    For an annotation adapter to the ExposureFile that will store a
    list of references to other notes.
    """

    active_notes = zope.schema.List(
        title=u'Active Notes',
        description=u'The list of notes that are active at this list of notes',
        default=[],
    )


class IRDFViews(zope.interface.Interface):
    """\
    Interface related to RDF views.
    """


class ICodeViews(zope.interface.Interface):
    """\
    Interface related to code views.
    """


class INamedUtilBase(zope.interface.Interface):
    """\
    Marker interface for the utility generator.
    """


class IDocViewGen(zope.interface.Interface):
    """\
    For the utilities that will generate the text for the document_view
    of exposure type objects.
    """

    title = zope.schema.Text(
        title=u'Title',
        description=u'Title of this generator',
        required=False,
    )

    description = zope.schema.Text(
        title=u'Description',
        description=u'A brief note about what this generator does.',
        required=False,
    )

    def generateTitle():
        """\
        The method that will generate the title.
        """

    def generateDescription():
        """\
        The method that will generate the description.
        """

    def generateText():
        """\
        The method that will generate the text.
        """


class IExposureDocViewGenForm(zope.interface.Interface):
    """\
    For the form and utility that handles the generation of the text for
    the ExposureFile default document_view.
    """

    docview_gensource = zope.schema.Choice(
        title=u'Documentation File',
        description=u'The file where the documentation resides in.  If this '
                     'object is already a file, leaving this field unselected '
                     'means the current file will provide the data from which '
                     'the document will be generated from.',
        vocabulary='ManifestListVocab',
        required=False,
    )

    docview_generator = zope.schema.Choice(
        title=u'View Generator',
        description=u'The selected generator will be used to attempt to ' \
                     'generate text for the default document view.',
        vocabulary='DocViewGenVocab',
        required=False,
    )


class IExposureRolloverForm(zope.interface.Interface):
    """
    """

    # XXX this should be some sort of radio choice, but I haven't
    # figured out how to integrate the radio widgets with the table.

    commit_id = zope.schema.TextLine(
        title=u'Commit ID'
    )

    exposure_id = zope.schema.TextLine(
        title=u'Exposure ID'
    )


class IExposurePortDataProvider(zope.interface.Interface):
    """\
    Provides generator whenever unknown datatypes are encountered.
    """


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


class IExposureDocViewGenSourceAdapter(zope.interface.Interface):
    """\
    Specific for DocViewGen, which has one exception case for IExposure
    types.
    """


class ICmetaNote(zope.interface.Interface):
    """\
    CellML Metadata note.
    """

    metadata = zope.schema.Text(
        title=u'Metadata',
        description=u'The metadata content',
    )

    model_title = zope.schema.TextLine(
        title=u'Model Title',
        description=u'Title of the model',
    )

    model_author = zope.schema.TextLine(
        title=u'Model Author',
        description=u'Author of the model',
    )

    model_author_org = zope.schema.TextLine(
        title=u'Model Author Organization',
        description=u'Organization which the author is part of',
    )

    citation_authors = zope.schema.List(
        title=u'Citation Authors',
        description=u'List of authors of this citation',
    )

    citation_title = zope.schema.TextLine(
        title=u'Citation Title',
        description=u'The title of this citation (e.g. the title of a journal article)',
    )

    citation_bibliographicCitation = zope.schema.TextLine(
        title=u'Bibliographic Citation',
        description=u'The source of the article',
    )

    citation_id = zope.schema.TextLine(
        title=u'Citation Id',
        description=u'The unique identifier for this citation (such as Pubmed).',
    )

    citation_issued = zope.schema.TextLine(
        title=u'Citation Datetime',
        description=u'Taken from dcterms:issued.  Since the datetime format can be unpredictable, plain text is used.',
    )

    keywords = zope.schema.List(
        title=u'Keywords',
        description=u'The keywords of this model.',
    )


class IOpenCellSessionNote(zope.interface.Interface):
    """\
    OpenCell Session Note
    """

    filename = zope.schema.Choice(
        title=u'Session File',
        description=u'The session file that is made for this file.',
        vocabulary='ManifestListVocab',
    )