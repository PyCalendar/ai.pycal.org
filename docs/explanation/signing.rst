====================
Signing an agreement
====================

What is signed
==============

An agreement is the file ``path`` of a repository at a commit. The recorded
commit is the **last edit of that file** within the configured ``ref``. The
site identifies a version by the **source repository, file-edit commit and path**:

- The same file at the same commit is the same agreement, also when several
  repositories ask for it, for example all repositories of an organization that
  point to one repository of agreements. People sign it once.
- An unrelated push, such as a README or configuration change, keeps the
  existing version and its signatures. Moving ``main`` alone creates no version.
- An edit of the agreement file creates a new version. Git can not say whether
  a change of wording changes the meaning, so every file edit needs a new signature.
  The page of the new version shows what changed since the version the person
  signed. Use a ``ref`` in the configuration file to choose when a new version
  is asked for.
- A tag or commit reference limits the file history to that point. A later
  edit on another branch does not affect the selected version. Deleting an
  agreement file reports an error; the site does not silently reuse its old text.

The text of each version is stored when it is first read, so that it is known
later what was signed, also if the repository changes or disappears.

Who signs
=========

People are identified by the id of their GitHub account, which stays when they
change their handle. The handle at the time of signing is stored with the
signature.

Why signing can not be automated
================================

An agreement is a decision of a person. The site makes sure that a person made
it, on the page of the agreement:

- There is no API and no token to sign. Signing needs a session of the site,
  which starts with signing in with GitHub in the browser.
- The form of the page contains a token that says to whom which version was
  shown, and when. A form without it, or with the token of another person or
  agreement, is refused
  (:class:`~ai_pycal.errors.signing.AgreementNotShown`).
- The box **I have read and accept this agreement** is ticked, and the person
  types their GitHub handle.
- The agreement is signed at least ``SIGN_MIN_SECONDS`` after it was shown,
  and at most ``SIGN_MAX_HOURS`` later.
- The forms are protected against cross-site requests, and the pages can not be
  shown in frames of other sites.
- The admin pages of the site can not add signatures.

A person who wants to can still write a program that uses their own session.
The steps above make sure that this is their own decision, not something done
on their behalf.

What the pull request shows
===========================

For each agreement, the pull request gets a check ``<site>/<agreement>``: *pending*
with a link to sign, or *success* when its author signed. The labels of
``pr.labels`` are set when the author signed and removed when the agreement
changed. Maintainers can make the checks required to merge.
