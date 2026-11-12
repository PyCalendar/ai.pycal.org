===================
Set up a repository
===================

This tutorial is for maintainers who want the contributors of a repository to
sign agreements. You need the role *admin* or *maintain* of the repository, and
the right to install GitHub Apps on its account or organization.

The site must already have its GitHub App configured. If you run the site,
first go to :doc:`/how-to/github-app` and choose the recommended submission
form, manifest CLI flow or manual creation. Then return here to install
that app and activate repositories.

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
       repository: https://github.com/PyCalendar/ai.pycal.org-example.git
       path: agreements/ai-policy.md
       pr:
         labels: ai-policy-accepted

All fields are described in :doc:`/reference/config-file`. The example
repository `PyCalendar/ai.pycal.org-example
<https://github.com/PyCalendar/ai.pycal.org-example>`_ contains two test
agreements.

3. Install the GitHub App
=========================

Sign in on the site with GitHub and open **Setup**. Select **Install the GitHub
App**. GitHub asks you to choose the repositories and to accept the permissions
listed in :doc:`/reference/permissions`. Afterwards GitHub sends you back to the
page **Setup**.

The site renews expiring GitHub user tokens automatically while you use setup.
If it shows **Your sign in with GitHub has expired**, sign out and sign in
again: the stored authorization can no longer be renewed. If GitHub is
temporarily unavailable, try again later.

4. Add the repository
=====================

On the page **Setup**, select **Add** next to the repository. The site reads the
configuration file and the agreements. If something is wrong, it shows the
error with a link to how to solve it, and the repository is not added.

Once added, the open pull requests get a check for each agreement, and those of
people who signed get the labels of ``pr.labels``.

.. _permission-email:

5. Enter an email address
=========================

When a new version of the site needs more permissions, the site writes to the
address of the installation and to its administrators who have an email address
on GitHub. Enter the address in **Email for new permissions** next to the
installation on the page **Setup**. The email links to the page of GitHub where
the owners of the installation accept the permissions; until then, the site
keeps working with the permissions it has. The permissions are listed in
:doc:`/reference/permissions`.

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
