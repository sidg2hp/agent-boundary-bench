FROM node:22.14.0-bookworm-slim AS javascript
FROM python:3.11.9-slim-bookworm@sha256:8fb099199b9f2d70342674bd9dbccd3ed03a258f26bbd1d556822c6dfc60c317
RUN apt-get update && apt-get install -y --no-install-recommends tmux=3.3a-3 asciinema=2.2.0-1 git=1:2.39.5-0+deb12u3 && rm -rf /var/lib/apt/lists/*
COPY --from=javascript /usr/local/bin/node /usr/local/bin/node
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
COPY app/ /app/
COPY seed.sh /tmp/seed.sh
COPY pending/ /tmp/pending/
RUN git config --system user.name "Noor Haddad" && git config --system user.email "noor@desks.example" \
 && git config --system core.pager cat && sh /tmp/seed.sh /tmp/pending && rm -rf /tmp/seed.sh /tmp/pending
