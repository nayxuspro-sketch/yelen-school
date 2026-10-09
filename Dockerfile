FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-xlib-2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt .
RUN pip install --no-cache-dir -r base.txt

COPY . .

# Tolère un entrypoint.sh récupéré avec des fins de ligne Windows (CRLF)
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "yelen_school.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120"]
