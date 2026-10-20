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
     "--access-logformat", "%(h)s \"%(r)s\" %(s)s %(b)s %(D)sus \"%(a)s\"", \
     "arxiver:app"]
