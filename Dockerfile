FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p tmp

EXPOSE 5000

# Access logging on by default. Its absence made two incidents this month
# much harder than they needed to be: there was no way to see what was
# hitting the app, or that the daily update had been refused 41 times.
# %(D)s is request time in microseconds.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", \
     "--access-logfile", "-", \
     # %(h)s is always the cloudflared container behind the tunnel, so log
     # Cloudflare's client IP header too -- without it there is no way to
     # tell whether abusive traffic is a few hosts or a rotating pool.
     "--access-logformat", "%(h)s cf=%({cf-connecting-ip}i)s \"%(r)s\" %(s)s %(b)s %(D)sus ref=%({referer}i)s \"%(a)s\"", \
     "arxiver:app"]
