# nevelib

A modular Python bioinformatics library for genomic sequence analysis.

Six module families — read preparation, assembly, homology search, clustering, multiple sequence alignment, and mapping — exposed as focused CLIs and importable Python modules.

Requires Python ≥ 3.11.

**Website:** [nevelib-website.vercel.app](https://nevelib-website.vercel.app/)

## Installation

```bash
pip install nevelib              # all six modules
pip install nevelib[viz]         # adds matplotlib, seaborn
pip install nevelib[confirm]     # adds pysam
pip install nevelib[all]         # viz + confirm
pip install nevelib[dev]         # all + pytest, pytest-cov
```

## Modules

| Module | Description | CLI |
|--------|-------------|-----|
| reads | BAM → FASTQ extraction, quality trimming, QC reporting | `nevelib-reads` |
| assembly | Digital normalization, de novo assembly, coverage filtering, deduplication | `nevelib-assembly` |
| search | BLAST-based homology search, hit parsing, filtering, classification | `nevelib-search` |
| clustering | Sequence clustering via MMseqs2 | `nevelib-clustering` |
| msa | Multiple sequence alignment via MAFFT | `nevelib-msa` |
| mapping | Pairwise and reference alignment via minimap2 | `nevelib-mapping` |

## Usage

Each module is invoked with a YAML configuration file:

```bash
nevelib-reads config.yaml
nevelib-assembly config.yaml
nevelib-search config.yaml
nevelib-clustering config.yaml
nevelib-msa config.yaml
nevelib-mapping config.yaml
```

Sample configs ship with each module. To copy one out:

```bash
python3 -c "import nevelib.reads; print(nevelib.reads.__path__[0])"
# then copy config.sample.yaml from the printed path
```

Modules are also importable directly:

```python
from nevelib.search.blast import run_blastn
from nevelib.clustering.mmseqs import run_mmseqs_linclust
from nevelib.msa.mafft import run_mafft
```

## External tool requirements

Each module wraps standard bioinformatics tools that must be available on `PATH`:

| Module | Required tools |
|--------|---------------|
| reads | samtools, fastp, fastqc, pigz |
| assembly | bbnorm.sh (BBTools), spades.py, mosdepth, blastn, samtools, pigz |
| search | blastn, blastx, makeblastdb |
| clustering | mmseqs |
| msa | mafft |
| mapping | minimap2 |

## License

MIT
