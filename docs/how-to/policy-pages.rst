=======================================
Contributor pages, choices and profiles
=======================================

The home page links to ``/projects/``, which lists the projects with their
status: whether the site checks their pull requests, or the error of their
configuration. The arrow of a project opens its agreements, mandatory ones
first. ``/projects/<owner>/`` lists the projects of one owner.

An agreement page such as ``/agreements/2/`` has the path of the agreement in
the site as its title: owner, project and agreement, each a link, with a menu
of the other agreements of the project. Its source and version are at the
bottom. The history of an agreement, ``/agreements/history/<source>/<path>/``,
shows each visible version and the projects using it.

A project page such as ``/project/collective/icalendar/`` lists policies,
choices and dated signatures. Contributors can set their default for future
PRs there. Defaults do not change existing PR choices.

The public contributor page ``/contributor/<github-handle>/`` shows signed
versions, signing dates, projects where each signature is currently valid,
and recorded PR choices. Projects the person has engaged with are shown
first; other projects are inside a collapsed details view. When viewing your
own page, review existing PRs after changing a default and change their choices
individually if appropriate.

Sign from a pull request
========================

``/project/collective/icalendar/pulls/123/`` is the focused check-details page.
It shows the PR author's current mandatory agreements and policy choice.
Everyone can read the public record. Only the author can change the choice
or sign for that PR. Other people may sign agreements on their own behalf
from the agreement pages.

Log in with GitHub, choose a policy bundle, and save it. Optionally also save
it as your default for future PRs. Expand any agreement to read its full text,
select its acceptance checkbox, type your GitHub handle and submit the form.
The page verifies its display tokens and minimum signing time. No API or
administrator action can sign for someone else.

This page and the login flow returning to it omit the footer and extra menu
links. The site name at the top left returns to the home page; login is at
the top right. ``/repository/<owner>/<repo>/pull/<number>/`` shows the same page; the older
``/<owner>/<repo>/pull/<number>/`` links redirect there.

Profile, email and project problems
===================================

``/profile/`` is private to the signed-in user. It lists projects for which
GitHub reports write, maintain or admin access, and links to email management.
Add an address and open the verification link in the email. Verification
requires confirmation on the site; merely loading the link does not verify it.
Signing in remains GitHub-only and does not require an email address.

Project problems, including missing agreement files and label-write permission
failures, appear as persistent messages with a description and documentation
link. Verified maintainers who opt in receive email for new or changed
problems. The same unresolved problem is not emailed repeatedly. Fixing it
clears the message; a recurrence can trigger another email. Email delivery
failures preserve the problem for a later retry.

The email preference on Profile opts out of individual project problem and
permission emails. Messages on the site remain visible. An installation's
explicitly configured shared notification address is independent of an
individual contributor's preference.

Private projects and their agreement records are excluded from public
responses. Signed-in contributors associated with a private project can
view its records. Email addresses and email preferences are never public.

Logs
====

Every webhook that GitHub sends to the site, and every action of a person such
as signing or **Update**, is a *trigger*. What follows from it is recorded as
*actions*, each with its reason: labels added to or removed from pull
requests, checks, the configuration read, new versions of agreements, emails.
A page only shows the triggers and actions that concern it, newest first; a
trigger opens to its actions, and triggers without actions are gray.

``/logs/project/<owner>/<repo>/``
   The log of a project, linked from the page of the project.
``/logs/project/<owner>/<repo>/pulls/<number>/``
   The log of a pull request, linked from its page.
``/logs/contributor/<handle>/``
   The log of a person: their signatures and their pull requests.
``/logs/all/``
   The global log, only for the administrators in ``SITE_ADMINS``, in the
   section *Administration* of the menu. It also shows what is not public:
   emails (without addresses), sign-ups, the registration of the app, refused
   webhooks and webhooks of repositories that the site does not know. On the
   other logs, administrators open a trigger in the global log with ⤢.
