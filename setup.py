from setuptools import setup, find_packages
import os

version = open(os.path.join('pmr2', 'app', 'version.txt')).read().strip()

setup(
    name='pmr2.app',
    version=version,
    description='The PMR2 Application',
    long_description=open('README.txt').read() + "\n" +
                     open(os.path.join('docs', 'HISTORY.txt')).read(),
    # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Framework :: Plone',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='',
    author='Tommy Yu',
    author_email='tommy.yu@auckland.ac.nz',
    url='http://www.cellml.org/',
    license='GPL',
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['pmr2'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'setuptools',
        'z3c.form',
        'Paste',
        'z3c.table>=0.6.0',
        'plone.app.content',
        'plone.app.z3cform>=0.3.2',
        'plone.z3cform>=0.5',
        'pmr2.mercurial',
        'lxml>=2.1.0',
        # -*- Extra requirements: -*-
    ],
    entry_points="""
    # -*- Entry points: -*-
    """,
    )
