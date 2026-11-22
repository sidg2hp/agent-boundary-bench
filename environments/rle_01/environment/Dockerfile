FROM python:3.11.9-slim-bookworm@sha256:8fb099199b9f2d70342674bd9dbccd3ed03a258f26bbd1d556822c6dfc60c317
RUN apt-get update && apt-get install -y --no-install-recommends tmux=3.3a-3 asciinema=2.2.0-1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
COPY app/ /app/
COPY seed.sh desk/ /desk/
RUN sh /desk/seed.sh && rm -rf /desk
