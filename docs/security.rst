========
Security
========

Report security issues privately with a `security advisory
<https://github.com/PyCalendar/sign.pycal.org/security/advisories/new>`_, not in
a public issue.

The site stores the GitHub id and handle of the people who sign in, the
signatures, the text of the agreements and the tokens of the sign in of
administrators. The private key of the GitHub App and the secret key are in
``DATA_DIR`` or the environment: keep them out of backups others can read.
