# cozystack-website

Cozystack.io website

## Prechecks
```bash
go version
hugo version
```

## Install go

You will need a go version 1.14 or higher to run the website.
[instructions](https://go.dev/doc/install)

```bash
 wget https://go.dev/dl/go1.24.2.linux-amd64.tar.gz -P /tmp
 rm -rf /usr/bin/go && sudo tar -C /usr/local -xzf /tmp/go1.24.2.linux-amd64.tar.gz
 export PATH=$PATH:/usr/local/go/bin
 go version
```

## Install hugo

Be sure to download the extended version of Hugo from the GitHub releases page. The binary that was installed by your
operating system package manager may (and most likely will) not work correctly.

```bash
brew install hugo
```

## Run docs

```bash
hugo serve
```

## Publishing tools

`hack/mcp/` holds two tools for the blog: one that creates a post, one that
checks posts. They share a single implementation, so a generated post and a
hand-written one are held to the same rules — closed taxonomy vocabularies,
resolvable internal links, a present description, and an Open Graph card social
parsers can actually render.

Check content before opening a pull request:

```bash
python3 hack/mcp/server.py --check
```

The same command runs in CI. `.mcp.json` registers the tools as an MCP server,
so an MCP-capable client picks them up from a checkout with no separate
installation.

See [`hack/mcp/README.md`](hack/mcp/README.md) for the tool reference, what the
checks cover, and what the tools deliberately leave alone.
