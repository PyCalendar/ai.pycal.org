"""Build the registration form with the application's current GitHub manifest."""

import html
import json
from pathlib import Path

from docutils import nodes
from docutils.parsers.rst import Directive

from ai_pycal.github.permissions import manifest


class GitHubAppForm(Directive):
    """Insert the documentation form with the required permissions and events."""

    def run(self) -> list[nodes.Node]:
        """Render the form using the same manifest as the management command.

        Returns:
            The raw HTML form as a documentation node.
        """
        template = Path(__file__).parents[1] / "_includes/github-app-form.html"
        self.state.document.settings.env.note_dependency(str(template))
        self.state.document.settings.env.note_dependency(
            str(Path(__file__).parents[2] / "ai_pycal/github/permissions.py")
        )
        specification = manifest("", "http://localhost:5000")
        rendered = template.read_text().replace(
            "__MANIFEST__", html.escape(json.dumps(specification), quote=True)
        )
        return [nodes.raw("", rendered, format="html")]


def setup(app) -> dict:
    """Register the documentation directive.

    Args:
        app: The Sphinx application.

    Returns:
        Extension metadata declaring safe parallel builds.
    """
    app.add_directive("github-app-form", GitHubAppForm)
    return {"version": "1", "parallel_read_safe": True, "parallel_write_safe": True}
