# PEN-STACK Streamlit UI image.
# Thin layer over the project image; serves the multi-page platform UI (incl. the Agent + Bridge pages).
FROM penstack:phase1
# bridge designer (Bridge design page) + scipy (validation); ViennaRNA/pysam are already in the base.
RUN pip install --no-cache-dir bridgernadesigner scipy
WORKDIR /work
COPY . /work
ENV PYTHONPATH=/work
EXPOSE 8501
CMD ["streamlit", "run", "pen_stack/ui/app.py", "--server.port", "8501", \
     "--server.address", "0.0.0.0", "--server.headless", "true"]
