FROM apache/superset:latest

USER root
RUN pip install psycopg2-binary sqlalchemy-redshift

USER superset

COPY superset_config.py /app/superset_config.py
ENV SUPERSET_CONFIG_PATH=/app/superset_config.py

# Initialize on first run
CMD ["sh", "-c", "superset db upgrade && superset fab create-admin --username admin --firstname Admin --lastname User --email admin@localhost --password ${SUPERSET_ADMIN_PASSWORD:-admin} || true && superset init && superset run -h 0.0.0.0 -p 8088"]
