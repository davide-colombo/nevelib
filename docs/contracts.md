# Data and failure contracts

## General rules

Public Python functions, result dataclasses, command names, configuration keys, and
serialized columns are compatibility surfaces. A change to one requires inspection of
direct callers and consumers. Keep output ordering deterministic wherever the current API
defines an order.

A valid empty result means the requested operation completed and found zero qualifying
records. A missing input, malformed required record, unavailable tool, nonzero tool exit,
or missing required tool artifact is a failure. Do not convert failures into an empty file,
zero count, pass-through result, or biological absence.

## Sequence records

- A FASTA identifier is the first whitespace-delimited token after `>`; descriptive text
  after that token is not part of record identity.
- Paired FASTQ inputs must be structurally valid and synchronized where the operation
  requires pairs. An empty mate cannot silently erase a non-empty mate.
- Sequence writers preserve identifiers and biological sequence content except for the
  transformation explicitly named by the function.

## Coordinates and strand

- Pairwise mApping Format (PAF) query and target coordinates are zero-based and
  end-exclusive.
- BLAST tabular coordinates retain BLAST's one-based inclusive convention at parse time.
  Subject coordinates are normalized to ascending order only where the API also preserves
  the derived strand.
- Interval filtering and containment comparisons must state which convention they accept;
  do not mix PAF and BLAST endpoints implicitly.

## BLAST hit tables

The default parser schema follows the configured BLAST outfmt fields. Filtering returns the
same container kind it receives: `list[BlastHit]` or `pandas.DataFrame`.

For object lists, a requested coverage threshold rejects a hit without usable coverage
evidence. For DataFrames, `min_qcov` requires one of `qcov`, `qcovhsp`, or `qcovs`, and
`min_scov` requires one of `scov`, `scovhsp`, or `scovs`. If the required column family is
absent, `filter_hits` raises `ValueError`; silently omitting the requested threshold is not
allowed. Present but non-numeric or missing cell values are coerced to missing and do not
pass the threshold.

Merged BLAST regions preserve normalized coordinates, query/scaffold identity, and
deterministic ordering. Taxonomy classification must keep unknown taxonomy distinct from a
negative biological classification.

## Tool wrappers

Wrappers validate required inputs before invocation and surface unavailable executables and
nonzero exits as exceptions with actionable context. SPAdes assembly succeeds only when it
produces a non-empty `scaffolds.fasta` or a non-empty `contigs.fasta`; contigs remain the
documented fallback when scaffolds are absent. A zero exit without either artifact raises
`RuntimeError`.

External tool arguments, filenames, and output schemas remain stable unless a task explicitly
authorizes the contract change and a regression proves the new boundary. Tool logs and
temporary state are diagnostic artifacts, not scientific evidence by themselves.

## Clustering and serialized tables

Cluster assignment parsing preserves member and representative identity and deterministic
row order. TSV writers retain declared column names, types, missing-value meaning, and row
identity. A schema change requires a coordinated producer-consumer change or an explicit
versioned successor.
