===================
Set up a repository
===================

This tutorial is for maintainers who want the contributors of a repository to
sign agreements. You need the role *admin* or *maintain* of the repository, and
the right to install GitHub Apps on its account or organization.

The site must already have its GitHub App configured. If you run the site,
first go to :doc:`/how-to/github-app` and choose the recommended submission
form, manifest CLI flow or manual creation. Then return here to install
that app on repositories.

1. Write the agreements
=======================

An agreement is a Markdown file in a repository on GitHub, such as
``agreements/ai-policy.md``. It starts with its title as a heading of level 1,
such as ``# AI Policy``: the site names the agreement by this title. The agreements can be in the repository itself or in another repository,
for example one repository with the agreements of all projects of an
organization.

Tag the commit of the agreement, so that it does not change by accident:

.. code-block:: shell

   git tag ai-policy-v1
   git push origin ai-policy-v1

2. Add the configuration file
=============================

Add ``.github/agreements.yml`` to the default branch of the repository:

.. code-block:: yaml

   version: 2.0.0
   agreements:
     ai-policy:
       name: AI Policy
       ref: ai-policy-v1
       repository: https://github.com/PyCalendar/sign.pycal.org-example.git
       path: agreements/ai-policy.md
       pr:
         labels: ai-policy-accepted

All fields are described in :doc:`/reference/config-file`. The example
repository `PyCalendar/sign.pycal.org-example
<https://github.com/PyCalendar/sign.pycal.org-example>`_ contains two test
agreements.

3. Install the GitHub App
=========================

Install the app from its page on GitHub, or open **Setup** on the site and
select **Install the GitHub App**. GitHub asks you to choose the repositories
and to accept the permissions listed in :doc:`/reference/permissions`.

That is the only step. GitHub only lets people who administer a repository
install an app on it, and tells the site with a signed webhook which
repositories you chose. You do not need to sign in on the site: each chosen
repository with the configuration file is set up, and its open pull requests
get a check for each agreement. Those of people who signed get the labels of
``pr.labels``. A repository without the file is set up when the file is pushed
to its default branch.

If the configuration file is wrong, the repository is not set up. Its error,
with a link to how to solve it, is shown on **Setup** and on the page of the
project; push a corrected file.

4. Remove or add a repository on Setup
======================================

On **Setup**, signed in, you see the repositories of your installations. The
site's app reads, with its own token, whether you have the role *admin* or
*maintain* of a repository; it does not act on your behalf on GitHub.

**Remove** stops checking the pull requests of a repository; the signatures
stay. A removed repository is not set up again by a push or a new installation,
only by **Add**.

.. _permission-email:

5. Emails: permissions and problems
===================================

The site writes two kinds of email:

New permissions
   When a new version of the site needs more permissions, the address in
   **Email of the installation** next to the installation on the page
   **Setup**, and the administrators of the installation, get the link to the
   page of GitHub where the owners accept them. Until then the site keeps
   working with the permissions it has. The permissions are listed in
   :doc:`/reference/permissions`.
Problems of a project
   On the page of a project, **Watch this project** sends you an email when
   the project has a problem, such as a configuration that cannot be read.
   Administrators who set up a repository watch it already.

Emails go to one address per person: your primary address on the site if it is
verified, otherwise your newest verified address, never one that is not
verified. Watching therefore needs a verified address. You can turn the emails
off in your preferences.

Update by hand
==============

The site reads the configuration on every push to the default branch. To read
it again by hand, such as after changing an agreement in another repository,
press **Update** below the pull requests on the page of the project. Each
administrator can do this once in 5 minutes; every update is in the log of the
project.

Changing the agreements
=======================

When you change the configuration file or the file of an agreement in the
default branch, the site reads it again. A new commit of an agreement needs a
new signature: the labels are removed from the pull requests of people who did
not sign the new version, and they see what changed when they open it.

Make the checks required
========================

To merge only pull requests whose authors signed, make the checks such as
``sign.pycal.org/ai-policy`` required in a rule of the default branch on GitHub.
