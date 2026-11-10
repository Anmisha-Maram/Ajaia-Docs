"""Allow-list HTML sanitizer.

Document content is stored as HTML and rendered for every collaborator, so it is
cleaned on every write. Only the tags the editor toolbar can produce survive.
"""
import nh3

ALLOWED_TAGS = {
    "h1", "h2", "h3", "p", "br", "strong", "em", "u", "s",
    "ul", "ol", "li", "blockquote", "a",
}
ALLOWED_ATTRIBUTES = {"a": {"href"}}
ALLOWED_SCHEMES = {"http", "https", "mailto"}


def clean_html(html: str) -> str:
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_SCHEMES,
    )
