=======================================
Contributor pages, choices and profiles
=======================================

The home page links to ``/projects/`` and ``/agreements/``. The first lists
projects; the second lists agreements, grouped by source repository
and path. An agreement page shows each visible version and the projects currently
using its exact commit.

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
