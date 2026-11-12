=============================
Permissions of the GitHub App
=============================

The GitHub App asks for as little as it needs. These are the permissions of
this version; :file:`ai_pycal/github/permissions.py` lists them, and a test
checks that this page names all of them.

Repository permissions
======================

.. list-table::
   :header-rows: 1

   * - Permission
     - Level
     - For
   * - ``metadata``
     - read
     - the repositories of the installation (every app has it)
   * - ``contents``
     - read
     - the configuration file and the files of the agreements
   * - ``pull_requests``
     - write
     - the labels of the pull requests
   * - ``statuses``
     - write
     - the checks of the pull requests, with the link to sign

Each is the narrowest permission for its purpose:

``metadata: read``
   Every GitHub App has it.
``contents: read``
   The site reads the configuration file, the files of the agreements and the
   commits that changed them, and never writes files.
``pull_requests: write``
   Labels of pull requests can be written with ``issues: write`` or
   ``pull_requests: write``; the latter does not give access to issues. It also
   covers reading the open pull requests.
``statuses: write``
   Commit statuses are narrower than check runs (``checks: write``).

The app asks for no permission of accounts or organizations, and no email
addresses. A test keeps this list exact: a new permission needs its reason here.

Events
======

``pull_request``
   A pull request was opened or changed: it is checked.
``push``
   The configuration file or an agreement may have changed: it is read again.
``repository``
   The default branch changed: the configuration is read again and the open
   pull requests are checked. A renamed or transferred repository keeps its
   records under the new name. It needs only ``metadata``.

An app subscribes to events in its settings on GitHub, under *Permissions and
events*: apps registered before an event was added do not receive it until it
is ticked there. The page **Setup** shows the administrators of the site which
events the app misses, with the link to its settings, and
``manage.py check_permissions`` prints them.

The events ``installation`` and ``installation_repositories`` are sent to every
app; they tell the site about new and removed installations and permissions.

Signing in
==========

People sign in with the GitHub App. Its tokens have no scopes: GitHub tells the
site the handle and id of the account. For administrators, the site also asks
GitHub which installations and repositories they can manage; they need the role
*admin* or *maintain* of a repository to add it.

Contributors give no other permission to the site.

When a new version needs more
=============================

When a new version of the site needs another permission, the page Setup shows
the missing permissions, and the administrators of each installation get one
email with the link to accept them (``manage.py check_permissions``). Until
then, pull requests can not be checked: the webhooks answer
:class:`~ai_pycal.errors.github.MissingPermissions`.
