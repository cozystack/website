# Publishing tools

Two tools for publishing to the blog: one that creates a post, one that checks
posts. They share a single implementation, so a generated post and a
hand-written one are held to the same rules.

Writing a markdown file into the right directory is not the hard part. Keeping
every post consistent with rules that live scattered across documentation,
templates and habit is. Each check here exists because the mistake it prevents
has already been made in this repository.

## Running the checker

```bash
python3 hack/mcp/server.py --check                       # every blog post
python3 hack/mcp/server.py --check --path content/en/blog/some-post.md
```

Exits non-zero when any post has an error, so it works as a CI step.

Link checking has two modes. If `public/` holds a build, links are resolved
against it, which is exact — those are the paths the site actually serves, and
an unresolved link is an error. Without a build, URLs are inferred from the
content tree, which is only approximate: Hugo derives them through permalinks,
per-page aliases and version directories. In that mode an unresolved link is a
warning, so the checker never fails on its own guesswork. Build first for a
strict run:

```bash
hugo --gc --minify && python3 hack/mcp/server.py --check
```

## Running the tests

```bash
python3 hack/mcp/test_mcp.py
```

Each test builds a throwaway site in a temporary directory. Nothing touches the
real content tree.

## Using it as an MCP server

`.mcp.json` in the repository root registers the server, so an MCP-capable
client picks it up from a checkout with no separate installation. It speaks MCP
over stdio as line-delimited JSON-RPC.

### publish_post

Creates a post from markdown: writes a page bundle when images are supplied and
a plain file otherwise, copies the images beside the markdown, appends the
standard community section, validates the result, and commits to a branch.
Validation runs before anything is written — and if a later step fails, whatever
was created is removed, so a failed publish never leaves debris behind.

Required: `title`, `description`, `author`, `body`, `article_types`, `topics`.
Optional: `images`, `doc_links`, `slug`, `date`, `branch`, `commit`.

Metadata is expected ready-made. Turning a Google Doc or a raw draft into
markdown and choosing sensible taxonomy terms is the calling agent's job; this
server only lays the result out correctly and refuses what breaks the rules.

Images are copied unchanged. Resizing and AVIF or WebP conversion belong to
Hugo, which processes bundle resources natively and encodes AVIF as of 0.162 —
there is no reason to keep a second implementation of that here.

### validate

The same checks with nothing written. Pass `path` for a single post, omit it for
the whole blog.

## What the checks cover

**Markdown only.** `.html` content is refused. Hugo denies `text/html` content
by default, as the fix for an XSS vulnerability, and this repository carries no
such files any more; one added by hand would break the build again.

**Taxonomy.** Terms must come from `data/taxonomy.yaml`, and the two axes must
stay separate — a genre in `topics` or a subject in `article_types` is an error.
The vocabularies are closed on purpose: a term invented while writing produces a
taxonomy page with one entry, which reads as thin content. One post once carried
an image filename among its topics, which is what an unchecked list eventually
yields.

**Structure.** `slug` matches the bundle directory, the date in the directory
matches the front matter, posts with local images live in a bundle, and a bundle
without assets is flagged as pointless.

**Open Graph card.** The first entry in `images` must exist, be raster, and be
roughly 1200×630. SVG, AVIF and WebP are refused for the card specifically:
Telegram, LinkedIn and other parsers do not render them in `og:image`, and the
Telegram preview is the reason the card exists. AVIF and WebP remain fine in the
article body.

**Description.** Required, since it feeds both the meta description and the
JSON-LD `BlogPosting`. An empty one yields an empty field in structured data and
no useful search snippet.

**Links.** Internal links must resolve, and a link pinning a docs version other
than the current one is flagged as something that will age out. Links into
`/docs/next/` are refused — that trunk is excluded from production builds.

## What these tools deliberately do not do

**Generate meta tags.** The SEO and structured-data setup already lives in
`layouts/partials/hooks/head-end.html`: canonical URLs, `noindex` for superseded
docs versions, JSON-LD for the organization, the site and every blog post, plus
`robots.txt`, `llms.txt` and Open Graph tags from Docsy. Emitting any of that
here would only conflict with it. The job is to guarantee the quality of the
fields those templates read.

**Touch documentation.** `content/*/docs/**` is out of scope. Versioning, the
`next/` trunk and pages generated from upstream belong to the release pipeline
in `cozystack/cozystack`.

**Touch translations.** The localization pipeline has its own review gates.

**Parse arbitrary formats.** Input is markdown.
