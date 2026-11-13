==============
sign.pycal.org
==============

`sign.pycal.org <https://sign.pycal.org>`_ lets contributors sign the agreements
that a project asks of them, such as an AI policy or a contributor license
agreement. The pull requests of the contributors show what they signed: the
GitHub App labels them and adds a check for each agreement.

- **Contributors** sign in with GitHub, read an agreement and accept it:
  :doc:`tutorial/sign`.
- **Maintainers** add a configuration file to their repository, install the
  GitHub App and add the repository: :doc:`tutorial/admin`.
- **People who run the site** create the GitHub App and start the container:
  :doc:`how-to/github-app` and :doc:`how-to/run-docker`.

.. note::

   Most of this project is written with AI: Claude Code makes the changes
   from the prompts of a person, who reviews them. The prompts are recorded in
   the commit messages, as the :doc:`contribute` page explains.

.. toctree::
   :maxdepth: 2

   tutorial/index
   how-to/index
   reference/index
   explanation/index
   contribute
   security
   changelog
