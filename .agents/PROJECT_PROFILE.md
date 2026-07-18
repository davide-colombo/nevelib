# nevelib public project profile

## Identity and layout

nevelib is a Python `>=3.11` alpha shared library. `src/nevelib` contains the six
module families (reads, assembly, search, clustering, MSA, mapping); its tests live
under `src/nevelib/tests`. `pyproject.toml` is the version, dependency, CLI, and
pytest-discovery source of truth.

## Setup and validation

Package installation and environment changes require authorization. The standard
setup command is `pip install -e .[dev]`; normal validation is
`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest`. It may require the documented
development dependencies. Runtime wrappers require their documented
bioinformatics executables on `PATH`; do not install them implicitly.

## Compatibility contracts

nexteveApp declares `nevelib>=0.6.0` and imports FASTA/config/tool, BLAST, and
clustering interfaces. Preserve public APIs, exception/valid-empty behavior, and
table schemas. FASTA record identifiers are the first whitespace-delimited header
token. PAF is zero-based and end-exclusive. BLAST hits retain normalized ascending
subject coordinates with derived strand. Cluster assignment ordering is deterministic.
Exact downstream schema-versioning and release-pin policy are unresolved.

## Data and action boundaries

Sample YAML files are tracked examples; configured inputs and outputs are external
to the source tree. Keep fixtures synthetic and outputs, scratch, caches, and logs
out of authoritative source locations. Report commands, evidence, compatibility
impact, and skipped validation. Git integration/release, remote access, transfer,
destructive work, production work, and environment mutation require explicit task
authorization.

## Skill policy

The manifest selects default discoverable review, implementation, test,
configuration, schema, sequence, grouping, science-integrity, and evidence skills.
Handoff, prompting, dossier, stage-contract, provenance, parallelism, and resume
skills are optional but not installed. Remote, production, Git-release, transfer,
failure-recovery, and output-hygiene skills are excluded from ordinary discovery.
