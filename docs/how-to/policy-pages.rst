=======================================
Contributor pages, choices and profiles
=======================================

The home page links to ``/projects/``, which lists the organizations and people
whose projects use the site. An organization opens to its projects, each with
its status (up to date, or the error of its configuration), and a project opens
to its agreements, mandatory ones first. ``/projects/<owner>/`` shows one owner.
A repository appears once an administrator added it on **Setup**.

An agreement page such as ``/agreements/2/`` has the path of the agreement in
the site as its title: owner, project and agreement, each a link. The arrow
between the project and the agreement opens the other agreements of the
project. Badges say whether the agreement is mandatory and whether you signed
it. Its version is the date of its last change, with the time only if the file
changed twice that day; times are in your local time. Its source and version are at the
bottom. The history of an agreement, ``/agreements/history/<source>/<path>/``,
shows each visible version with the projects that asked for it, and whether
each asked for it as mandatory or optional: that belongs to the version of the
configuration, so it can differ between versions.

A project page such as ``/project/collective/icalendar/`` lists the
agreements with their badges, the choices and the open pull requests (**All
pull requests** shows the closed ones too). A pull request is green when all its
agreements are signed, yellow when only optional ones are missing, red when a
needed agreement is missing or it was closed without merge, and purple when it
was merged. The gear of an agreement shows its version, file, commit and
repository, the labels it sets (each a link to the pull requests with the label)
and the configuration file on the default branch. The log icon next to the title
leads to the log of the project, and the badge *Up to date* or *Error* to
``/project/<owner>/<repo>/status/``: the time of the last check, the format of
the configuration, and on an error what failed and how to fix it. Contributors can set their default for future
PRs there. Defaults do not change existing PR choices.

The public contributor page ``/contributor/<github-handle>/`` lists the newest
signature of each agreement: outdated ones first (a project asks for a newer
version), then valid ones with a green check and the projects where they are
valid. Each has its badges and the gear with its version. Then come the pull
requests with their state. Projects the person has engaged with are shown
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
the top right. The older addresses ``/repository/<owner>/<repo>/...`` and
``/<owner>/<repo>/...`` redirect to ``/project/...``.

Administrators of the site (``SITE_ADMINS``) can remove their own signature on
the page of an agreement, to test what follows: their pull requests are checked
again and the log records it.

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
trigger opens to its actions, and triggers without actions are gray. The title
of a log is its path: each part leads to the combined log of that level, and a
link leads back to the page of the project, pull request or person.

``/logs/<owner>/``
   The combined log of the projects of an organization or person.
``/logs/<owner>/<repo>/``
   The log of a project, linked with the log icon next to the title of the
   project.
``/logs/<owner>/<repo>/pulls/<number>/``
   The log of a pull request, linked from its page.
``/logs/contributor/<handle>/``
   The log of a person: their signatures and their pull requests.
``/logs/all/``
   The global log, only for the administrators in ``SITE_ADMINS``, in the
   section *Administration* of the menu. It also shows what is not public:
   emails (without addresses), sign-ups, the registration of the app, refused
   webhooks and webhooks of repositories that the site does not know. On the
   other logs, administrators open a trigger in the global log with ⤢.
