# Xeelo site working copies

This repository is the **private** git root for all Xeelo sites used with a XeeloKB clone. It belongs at:

```text
<XeeloKB>/projects/
```

Each site is a folder: `lz/`, `ovnet/`, … — not a separate git repo.

Full workflow lives in the parent XeeloKB clone: `docs/projects.md`. Typical tree per site:

```text
<name>/
  conventions.md           # site rules (language, naming); agent reads before object work
  .xeelo-connection.json   # gitignored — Admin URL, siteId, credentials
  snapshots/               # DB transfer ZIP/XML — gitignored; refresh with /download-db
  env/                     # extracted specs (versioned)
  changes/<loop-slug>/     # change loops + generated Object Transfer (versioned)
```

Do not add this tree to the public XeeloKB repository. Pull KB updates in the XeeloKB root; pull site updates here.
