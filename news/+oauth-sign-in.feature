People sign in with an OAuth app without scopes, so GitHub no longer asks them
to let the app act on their behalf; administrators enter it on Setup. The app
reads the roles of administrators with its own token; the site keeps no tokens
of people.
