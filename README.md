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
wget https://github.com/gohugoio/hugo/releases/download/v0.122.0/hugo_extended_0.122.0_linux-amd64.tar.gz
tar -xzf hugo_extended_0.122.0_linux-amd64.tar.gz
 chmod +x /usr/local/bin/hugo
```

## Run docs

```bash
hugo serve
```
