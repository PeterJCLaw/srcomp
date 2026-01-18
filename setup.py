from setuptools import find_namespace_packages, setup

with open('README.rst') as f:
    long_description = f.read()

setup(
    name='sr.comp',
    version='1.12.0',
    url='https://github.com/PeterJCLaw/srcomp/wiki',
    project_urls={
        'Documentation': 'https://srcomp.readthedocs.org/',
        'Code': 'https://github.com/PeterJCLaw/srcomp',
        'Issue tracker': 'https://github.com/PeterJCLaw/srcomp/issues',
    },
    packages=find_namespace_packages(include=['sr.*']),
    package_data={'sr.comp': ['py.typed']},
    namespace_packages=['sr', 'sr.comp'],
    description="Reliable software for running robotics competitions",
    long_description=long_description,
    author="Student Robotics Competition Software SIG",
    author_email='srobo-devel@googlegroups.com',
    install_requires=[
        'PyYAML >=5.1.2, <7',
        'league-ranker >=0.1, <2',
        'python-dateutil >=2.7, <3',
        'typing-extensions >=4.5, <5',
    ],
    python_requires='>=3.10',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: 3.14',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Libraries',
    ],
    zip_safe=True,
)
