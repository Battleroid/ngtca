FROM python:3.8.1

ENV CONFLUENCE_ENDPOINT "https://confluence.example.com"
ENV CONFLUENCE_USER user
ENV CONFLUENCE_PASS pass

COPY . /ngtca
WORKDIR /ngtca
RUN pip install .
VOLUME ["/docs"]
ENTRYPOINT ["ngtca"]
