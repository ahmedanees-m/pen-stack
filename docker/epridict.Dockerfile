# ePRIDICT (Mathis et al., Nat Biotechnol 2025, 10.1038/s41587-024-02268-2) — prime-editing-efficiency predictor
# from K562 chromatin context. Used ONLY as a comparator for the WS-PRIORART distinctness analysis (does the
# PEN-STACK durability axis capture something distinct from ePRIDICT's editing-efficiency axis?). Never in the app.
#
# The 6 light-model ENCODE bigWig tracks (5.3 GB) are NOT baked into the image — they are downloaded once to a host
# directory and MOUNTED at runtime over /epridict/bigwig. This keeps the image lean and the (public ENCODE) data
# external + re-usable. `curl` is installed so the upstream download script works if you prefer to bake instead.
#
#   # one-time download to a host dir (image already provides the accessions in epridict_download_encode.sh):
#   docker run --rm -v ~/epridict_bigwig:/dl --entrypoint bash epridict:tools -lc \
#     'cd /dl && for a in ENCFF139KZL ENCFF834SEY ENCFF959YJV ENCFF601JGK ENCFF954LGE ENCFF972GVB; do \
#        wget -q --tries=3 --timeout=120 "https://www.encodeproject.org/files/$a/@@download/$a.bigWig" -O "$a.bigWig"; done'
#
#   # batch prediction with the host bigWigs mounted read-only:
#   docker run --rm -v ~/work:/work -v ~/epridict_bigwig:/epridict/bigwig --entrypoint bash epridict:tools -lc \
#     'cd /epridict && cp /work/loci.csv input/ && conda run -n epridict python epridict_prediction.py batch loci.csv'
#
# NOTE: the upstream epridict_download_encode.sh calls `curl` (not wget); the stock miniconda base lacks curl, so an
# in-build `echo yes | bash epridict_download_encode.sh light` silently reports "Failed to download" for all 6 files.
# Installing curl below fixes that if you do choose to bake the data in.
FROM continuumio/miniconda3:24.9.2-0

RUN apt-get update && apt-get install -y --no-install-recommends git wget curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 https://github.com/Schwank-Lab/epridict.git /epridict
WORKDIR /epridict
RUN conda env create -f epridict_env.yml && conda clean -afy
RUN chmod +x epridict_download_encode.sh
# Data is mounted at runtime (see header). To bake instead, uncomment:
# RUN conda run -n epridict bash -c "echo yes | bash epridict_download_encode.sh light"
