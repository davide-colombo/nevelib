# nevelib

A modular bioinformatics library for genomic sequence analysis.

## Modules

| Module | Description | CLI |
|--------|-------------|-----|
| **reads** | BAM → FASTQ extraction, quality trimming, QC reporting | `nevelib-reads` |
| **assembly** | Digital normalization, de novo assembly, coverage filtering, deduplication | `nevelib-assembly` |
| **search** | BLAST-based homology search, hit parsing, filtering, classification | `nevelib-search` |
| **clustering** | Sequence clustering via MMseqs2 | `nevelib-clustering` |
| **msa** | Multiple sequence alignment via MAFFT | `nevelib-msa` |
| **mapping** | Pairwise/reference alignment via minimap2 | `nevelib-mapping` |

## Installation

```bash
pip install nevelib              # core (reads, assembly, search, clustering)
pip install nevelib[viz]         # adds matplotlib, seaborn
pip install nevelib[confirm]     # adds pysam (for BAM-level confirmation)
pip install nevelib[all]         # everything
pip install nevelib[dev]         # development dependencies
```

## Usage

Each module is invoked with a single YAML configuration file:

```bash
nevelib-reads config.yaml
nevelib-assembly config.yaml
nevelib-search config.yaml
```

Copy the sample config from each module directory and edit it:

```bash
cp $(python -c "import nevelib.reads; print(nevelib.reads.__path__[0])")/config.sample.yaml my_reads_config.yaml
```

Each module can also be used as a Python library:

```python
from nevelib.search.blast import run_blastn
from nevelib.clustering.mmseqs import run_mmseqs_linclust
from nevelib.msa.mafft import run_mafft
```

## External tool requirements

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
