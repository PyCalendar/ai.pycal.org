======================
The configuration file
======================

Projects define policies in ``.github/agreements.yml`` on their default branch.
The site reads the file on setup, on relevant pushes and with **Update** on the
page of the project. Version ``2.2.0`` uses ``ref``, ``pr.labels``,
``pr.unsigned-labels`` and ``sign-min-seconds`` and supports mandatory
agreements and choices.

.. code-block:: yaml

   version: 2.2.0
   agreements:
     cla:
       name: Contributor agreement
       sign-min-seconds: 30
       description: Everyone accepts the contributor agreement.
       path: agreements/cla.md
       ref: main
       mandatory: true
       pr:
         labels: [cla-signed]
         unsigned-labels: [cla-missing]
     disclosed-ai:
       name: AI use with disclosure
       description: Explain which tools assisted your contribution.
       path: agreements/disclosed-ai.md
       mandatory: false
     human-only:
       name: Human authorship
       description: Confirm that this contribution was made without AI.
       path: agreements/human-only.md
       mandatory: false
   choices:
     - name: Disclosed AI use
       description: Accept the AI policy and disclose the assistance.
       agreements: [disclosed-ai]
       default: true
       pr:
         labels: [ai-disclosed]
     - name: Human authorship
       description: Follow the human authorship policy instead.
       agreements: [human-only]
       default: false
       pr:
         labels: [human-authored]

Versions
========

``version`` is required and contains three numbers. The site reads versions
``1.x`` and ``2.x``; other major versions are refused. Unknown fields are
rejected for the supported minor version. A newer minor version of the same
major version permits unknown fields.

Version ``1.0.0`` uses ``tag`` and required ``pr.tags`` fields and treats every
agreement as mandatory. Existing configurations continue to work. To migrate,
set ``version: 2.0.0``, rename ``tag`` to ``ref`` and ``pr.tags`` to
``pr.labels``. Version 2 rejects the old names to expose typing errors.

Version ``2.1.0`` adds ``pr.unsigned-labels`` and version ``2.2.0`` adds
``sign-min-seconds``. Files of versions ``2.0.0`` and ``2.1.0`` keep working
unchanged.

Agreements
==========

``agreements`` is a nonempty mapping from policy identifiers to agreements.
Identifiers contain lowercase letters, digits, ``-`` and ``_``, start with a
letter or digit and have at most 50 characters. These identifiers appear in
GitHub check names and the contributor JSON and badge endpoints.

``name``
   Required. The human-readable policy name.

``description``
   Optional inline Markdown explaining this policy. Embedded HTML is escaped.
   The agreement file itself contains the full text being signed.

``path``
   Required. A relative path without ``..`` in the source repository. The file
   must be Markdown in UTF-8, at most 200 KB, and start with its title as a
   heading of level 1, such as ``# Contributor License Agreement``. The site
   names the agreement by this title everywhere; a file without one stops the
   configuration with :class:`~ai_pycal.errors.config_file.AgreementTitleMissing`.
   Markdown is rendered safely.

``repository``
   The source repository as ``owner/name``, an HTTPS GitHub URL or an SSH Git
   remote. Defaults to the project containing the configuration file.

``ref``
   A tag, branch or commit. Defaults to the source repository's default branch.
   The stored agreement version uses the last commit that edited its file
   within this reference. Unrelated pushes to the branch keep the same version
   and signatures. Tags and commit references select the file history up to
   that point.

``mandatory``
   A YAML boolean, default ``true``. Mandatory agreements apply to every PR.
   Agreements with ``mandatory: false`` apply when a selected choice lists them.
   Other optional agreements can be read and signed independently without
   blocking a PR.

``sign-min-seconds``
   Optional, since version ``2.2.0``. The time in seconds between opening the
   agreement and signing it, at least: a number from 0 to 3600. Without it,
   the site's setting ``SIGN_MIN_SECONDS`` applies, 3 seconds by default.
   If projects ask for the same agreement with different times, the longest
   time applies. Signing faster shows
   :class:`~ai_pycal.errors.signing.SignedTooFast`.

``pr.labels``
   Optional label or list of labels, each nonempty and at most 50 characters.
   Omit ``pr`` or use ``labels: []`` if the agreement grants no labels. An
   agreement's labels apply when it is required on the PR and signed. Shared
   labels require all applicable agreements that grant them to be signed.

``pr.unsigned-labels``
   Optional label or list of labels, since version ``2.1.0``. They are set
   while the agreement is required on the PR and not signed, and removed when it
   is signed, such as ``cla-missing``. A label shared by several agreements
   stays while any of them is unsigned.

Choices
========

``choices`` is an optional list of alternatives. Each choice contains:

``name``
   A unique name of at most 200 characters. Its lowercase, hyphenated form is
   the stable choice identifier, at most 50 characters. Keep this name stable
   when updating its contents; renaming it creates a different choice.

``description``
   Required Markdown explaining the choice.

``agreements``
   A nonempty list of policy identifiers defined under ``agreements``. Every
   agreement in the chosen bundle must be signed alongside the mandatory ones.

``default``
   A YAML boolean, default ``false``. At most one project choice may be the
   default. Without a default, contributors must explicitly select a choice.

``pr.labels``
   Optional labels for this choice. They reflect the saved selection, including
   while signatures are pending. The PR checks independently enforce all
   mandatory and selected agreements. A label also granted by an applicable
   agreement still requires that agreement's signature.

A contributor can set their own default for a project. It takes precedence
over the project's default when a **new PR is first recorded**. The choice
is then saved on that PR. Changing either default leaves existing PRs alone.
The contributor page lists existing PRs so the author can change each one.
Only the PR author may change its choice. Changing a choice never signs an
agreement, and previous signatures remain recorded for the agreement.

If a configured choice is removed or renamed, affected PRs require a fresh
selection. The site does not silently replace it with another default.

Labels and checks
=================

Only labels managed by the site's policy configuration are removed. Labels
from other workflows remain. Switching choices removes the old choice's
labels and obsolete optional-agreement labels. Labels removed from a later
configuration are also cleaned up on the next check.

Mandatory and selected agreements have success or pending checks. Agreements
outside the selected bundle have successful checks explaining that they are
not required, so a previous pending check cannot keep blocking the PR.
``choices/selection`` tracks the selected bundle and ``configuration/setup``
reports invalid project setup. Retired checks are marked successful.

Agreements and signatures
=========================

An agreement is identified by its **source repository URL and path**.
Versions also include the exact commit that last edited the file. Different projects can use different
commits of the same agreement at the same time. One signature covers all
projects using the same source, path and file-edit commit. Editing the file
needs a new signature; unrelated repository commits do not. Existing signatures
are preserved.
