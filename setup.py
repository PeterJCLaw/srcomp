from setuptools import find_packages, setup

with open('README.rst') as f:
    long_description = f.read()

setup(
    name='sr.comp',
    version='1.3.0',
    packages=find_packages(exclude=('tests',)),
    package_data={'sr.comp': ['py.typed']},
    namespace_packages=['sr', 'sr.comp'],
    description="Student Robotics Competition Software",
    long_description=long_description,
    author="Student Robotics Competition Software SIG",
    author_email='srobo-devel@googlegroups.com',
    install_requires=[
        'PyYAML >=3.11, <5',
        'league-ranker <0.1',
        'python-dateutil >=2.2, <3',
        'typing-extensions >= 3.7.4.2',
    ],
    # Note: there are known timezone issues in 3.5.0 (see https://bugs.python.org/issue23600)
    python_requires='>=3.5.1',
    setup_requires=[
        'Sphinx >=3.0.2, <4',
    ],
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Libraries',
    ],
    test_suite='tests',
    zip_safe=True,
)
