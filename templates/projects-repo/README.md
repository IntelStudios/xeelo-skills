# Xeelo site working copies

This repository is the **private** git root for all Xeelo sites used with a xeelo-skills clone. It belongs at:

```text
<xeelo-skills>/projects/
```

Each site is a folder: `lz/`, `ovnet/`, … — not a separate git repo.

Full workflow lives in the parent xeelo-skills clone: `docs/projects.md`. Typical tree per site:

```text
<name>/
  conventions.md           # site rules (language, naming); agent reads before object work
  .xeelo-connection.json   # gitignored — xeeloUrl + GraphQL admin token
  snapshots/               # DB transfer JSON — gitignored; refresh with /download-db
  env/                     # extracted specs (versioned)
  changes/<loop-slug>/     # change loops + generated Object Transfer (versioned)
```

Do not add this tree to the public xeelo-skills repository. Pull KB updates in the xeelo-skills root; pull site updates here.
