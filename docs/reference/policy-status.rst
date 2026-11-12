==============================
Contributor policy status API
==============================

Read a contributor's signature for a project's **current policy version**:

.. code-block:: text

   GET /project/collective/icalendar/contributor/<handle>/<policy-id>.json

Example response:

.. code-block:: json

   {
     "project": "collective/icalendar",
     "contributor": "alice",
     "policy": "ai-policy",
     "signed": true,
     "signed_at": "2026-11-10T12:00:00+00:00",
     "mandatory": true,
     "agreement": {
       "repository": "https://github.com/collective/icalendar",
       "path": "agreements/ai-policy.md",
       "commit": "0123456789012345678901234567890123456789"
     }
   }

``signed`` is false and ``signed_at`` is null when the current commit has not
been signed, including when the handle has no known signature. A changed
agreement commit invalidates current status while preserving old signatures.
The returned commit is the file's last edit within the configured reference;
unrelated pushes leave it unchanged. This reports a signature, not whether
every PR selected the policy.

Use the same URL with ``.svg`` instead of ``.json`` for an SVG badge:

.. code-block:: markdown

   [![AI policy](https://sign.pycal.org/project/collective/icalendar/contributor/alice/ai-policy.svg)](https://sign.pycal.org/contributor/alice/)

Both representations return ``Cache-Control: no-store``. Unknown projects or
policy identifiers return a JSON 404 error with ``error``, ``title``, ``detail``
and ``documentation`` fields. Private project records
are unavailable to anonymous visitors. These endpoints are read-only and
cannot create signatures or change choices.
