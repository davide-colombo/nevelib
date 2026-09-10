# Architecture

## Purpose and boundary

nevelib is an importable Python library with six command-line entry points. It validates
local inputs, builds commands for established bioinformatics tools, parses their outputs,
and exposes deterministic Python records and tables. External executables do the
resource-intensive analysis; nevelib owns validation, invocation, parsing, filtering, and
the published file contracts around those tools.

`pyproject.toml` defines the package, Python requirement, dependencies, command entry
points, and packaged sample configurations. Source is under `src/nevelib`; focused tests
are under `src/nevelib/tests`.

## Package layout

| Package | Responsibility | External tools |
| --- | --- | --- |
| `_common` | FASTA, FASTQ, BAM, BLAST database, compression, YAML, TSV, and process helpers | samtools and configured compressors where invoked |
| `reads` | BAM read extraction, trimming, and quality-control orchestration | samtools, fastp, FastQC, pigz |
| `assembly` | paired-read normalization, SPAdes assembly, coverage filtering, and self-BLAST deduplication | BBNorm, SPAdes, minimap2, samtools, mosdepth, BLAST+, pigz |
| `search` | BLAST execution, tabular parsing and filtering, interval merging, and taxonomy classification | BLAST+ |
| `clustering` | MMseqs2 linclust invocation and assignment parsing | MMseqs2 |
| `msa` | MAFFT invocation and alignment metrics | MAFFT |
| `mapping` | minimap2 invocation, Pairwise mApping Format parsing, filtering, and summaries | minimap2 |

Each public command reads one YAML file, merges documented defaults, validates required
input, creates its configured output directory, runs the selected tool steps, and validates
the resulting files unless validation is explicitly disabled. The sample YAML beside each
module is the user-facing configuration example.

## Dependency direction

Feature packages may depend on `_common`; `_common` does not depend on feature packages.
Command modules compose functions from their own feature package. Consumers may import
functions directly, so a module name beginning with an underscore is not proof that it is
unused externally. Changes must inspect known consumers before altering signatures, return
types, coordinate semantics, schemas, or failure behavior.

## State and reproducibility

The library stores no database and owns no production dataset. State consists of caller
inputs, configured output directories, tool logs, and serialized results. Reproducibility
therefore depends on the exact nevelib source or release, Python environment, configuration,
input/reference identity, and external-tool versions. The library does not make an
unversioned external executable reproducible by wrapping it.

See `contracts.md` for stable data behavior and `operations.md` for setup, validation,
runtime, and release evidence.
