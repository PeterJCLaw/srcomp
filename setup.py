from setuptools import find_namespace_packages, setup

with open('README.rst') as f:
    long_description = f.read()

setup(
    name='sr.comp',
    version='1.7.0',
    url='https://github.com/PeterJCLaw/srcomp/wiki',
    project_urls={
        'Documentation': 'https://srcomp.readthedocs.org/',
        'Code': 'https://github.com/PeterJCLaw/srcomp',
        'Issue tracker': 'https://github.com/PeterJCLaw/srcomp/issues',
    },
    packages=find_namespace_packages(exclude=('tests',)),
    package_data={'sr.comp': ['py.typed']},
    namespace_packages=['sr', 'sr.comp'],
    description="Reliable software for running robotics competitions",
    long_description=long_description,
    author="Student Robotics Competition Software SIG",
    author_email='srobo-devel@googlegroups.com',
    install_requires=[
        'PyYAML >=3.11, <7',
        'league-ranker >=0.1, <2',
        'python-dateutil >=2.2, <3',
        'typing-extensions >= 3.7.4.2',
    ],
    python_requires='>=3.7',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Libraries',
    ],
    zip_safe=True,
)
