Compstate Repositories
======================

Compstate repositories contain the entire state of the competition at a certain
time.

Their directory structure looks something like this:

.. code::

   ├── arenas.yaml
   ├── awards.yaml
   ├── [deployments.yaml]
   ├── [external]
   │   └── [any].yaml
   ├── league
   │   └── [arena]
   │       └── [match].yaml
   ├── knockout
   │   └── [arena]
   │       └── [match].yaml
   ├── league.yaml
   ├── schedule.yaml
   ├── scoring
   │   ├── score.py
   │   ├── [converter.py]
   │   └── [update.html]
   ├── shepherding.yaml
   └── teams.yaml
