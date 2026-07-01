# Cas-OFFinder genome-wide off-target enumerator (PEN-OFFTGT v2, O-WS1).
# The field-standard exhaustive PAM+mismatch(+bulge) genome scanner (Bae, Park & Kim, Bioinformatics 2014,
# 10.1093/bioinformatics/btu048). Runs ONLY on the VM over GRCh38; the live app replays the committed coordinate
# cache or abstains (the enumerated coordinates are facts from the public genome, no license restriction).
# CPU OpenCL via pocl so it runs without a GPU driver dependency (the "C" device); the VM GPU can be used with "G".
FROM continuumio/miniconda3:24.9.2-0

RUN conda install -y -n base -c conda-forge -c bioconda cas-offinder pocl ocl-icd-system \
    && conda clean -afy

# smoke: cas-offinder prints its usage banner (exits non-zero with no args, so guard it)
RUN cas-offinder 2>&1 | head -3 || true

WORKDIR /work
