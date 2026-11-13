=================
JSON of the pages
=================

Every public page has its information as JSON at the address of the page with
``.json`` instead of the last ``/``. The start page has ``/index.json``.

.. list-table::
   :header-rows: 1

   * - Page
     - JSON
   * - ``/``
     - ``/index.json``
   * - ``/projects/``, ``/projects/<owner>/``
     - ``/projects.json``, ``/projects/<owner>.json``
   * - ``/project/<owner>/<name>/``
     - ``/project/<owner>/<name>.json``: agreements with their signatures,
       choices and pull requests; ``?pulls=all`` also the closed ones
   * - ``/project/<owner>/<name>/status/``
     - ``/project/<owner>/<name>/status.json``: the configuration and its
       errors
   * - ``/project/<owner>/<name>/pulls/<number>/``
     - ``/project/<owner>/<name>/pulls/<number>.json``: the choice and whether
       each agreement is required and signed
   * - ``/contributor/<handle>/``
     - ``/contributor/<handle>.json``: signatures, pull requests and defaults
   * - ``/agreements/<id>/``
     - ``/agreements/<id>.json``: the text, its translations and the projects
       that ask for it
   * - ``/agreements/<id>/changes/<old>/``
     - ``/agreements/<id>/changes/<old>.json``
   * - ``/agreements/history/<owner>/<name>/<path>/``
     - ``/agreements/history/<owner>/<name>/<path>.json``
   * - ``/logs/<owner>/``, ``/logs/<owner>/<name>/``, ``…/pulls/<number>/``,
       ``/logs/contributor/<handle>/``
     - The same with ``.json``; ``?page=2`` for older entries
   * - ``/about/``, ``/licenses/``
     - ``/about.json``, ``/licenses.json``

The JSON holds what a visitor who is not signed in sees, also when the request
carries the cookie of a session: private projects are never in it. Pages for
signed-in people, such as ``/todos/`` or ``/setup/``, have no JSON.

Each project, pull request, person and agreement in the JSON has ``page`` and
``json``: the path of its page and of its JSON on the site, so a script can
follow them. Times are in ISO 8601 with their time zone.

Read it from other sites
========================

Every answer has the headers of CORS, ``Access-Control-Allow-Origin: *``, so
JavaScript on any site can read it:

.. code-block:: javascript

   const site = "https://sign.pycal.org";
   const project = await (await fetch(`${site}/project/PyCalendar/sign.pycal.org-example.json`)).json();
   for (const pull of project.pull_requests) {
     console.log(`#${pull.number} ${pull.state} by @${pull.author.login}`);
   }

The JSON can only be read: ``GET``, ``HEAD`` and ``OPTIONS``. Other methods
answer ``405``.

Errors
======

A missing page answers with its status and the error as JSON, such as:

.. code-block:: json

   {
     "error": "RepositoryNotFound",
     "title": "The repository was not found",
     "detail": "PyCalendar/nothing",
     "documentation": "https://docs.sign.pycal.org/reference/errors.html#ai_pycal.errors.setup.RepositoryNotFound"
   }

An address of no public page answers ``404`` with ``"error": "NotFound"``.

The status of one agreement of a person, with a badge, is in
:doc:`policy-status`.
