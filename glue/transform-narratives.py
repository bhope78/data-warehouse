"""
Glue ETL — Narrative List → catt.narratives

Reads raw JSON from S3, cleans columns, and upserts into Redshift Serverless.
"""

import sys
from datetime import datetime

from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from pyspark.sql.types import DateType, TimestampType, IntegerType

args = getResolvedOptions(sys.argv, ["JOB_NAME", "S3_RAW_PATH", "REDSHIFT_CONNECTION"])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

logger = glueContext.get_logger()

# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------

s3_path = args["S3_RAW_PATH"]
logger.info(f"Reading narratives from {s3_path}narratives.json")

df = spark.read.json(f"{s3_path}narratives.json")
logger.info(f"Raw record count: {df.count()}")

# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------

COLUMN_MAP = {
    "id": "id",
    "Title": "title",
    "Incident_x0020_Number": "incident_number",
    "Run_x0020_Number": "run_number",
    "Incident_x0020_Date": "incident_date",
    "Disposition": "disposition",
    "Chief_x0020_Complaint": "chief_complaint",
    "Chief_x0020_Narrative": "chief_narrative",
    "ClientProfile": "client_profile",
    "HousingStability": "housing_stability",
    "CrewFirstName": "crew_first_name",
    "CrewLastName": "crew_last_name",
    "Crew_x0020_Member_x0020_Level": "crew_member_level",
    "IsLock": "is_lock",
    "PD_CallOutReason": "pd_call_out_reason",
    "Source": "source",
    "Created": "sp_created",
    "Modified": "sp_modified",
}

existing_cols = set(df.columns)
select_exprs = []
for sp_col, rs_col in COLUMN_MAP.items():
    if sp_col in existing_cols:
        select_exprs.append(F.col(sp_col).alias(rs_col))

df = df.select(select_exprs)

# If incident_number is null, fall back to title
if "incident_number" in df.columns:
    df = df.withColumn(
        "incident_number",
        F.coalesce(F.col("incident_number"), F.col("title")),
    )

# Cast types
if "incident_date" in df.columns:
    df = df.withColumn("incident_date", F.to_date(F.col("incident_date")))

for col_name in ["sp_created", "sp_modified"]:
    if col_name in df.columns:
        df = df.withColumn(col_name, F.to_timestamp(F.col(col_name)))

if "id" in df.columns:
    df = df.withColumn("id", F.col("id").cast(IntegerType()))

# Clean narrative text — strip HTML tags if present
if "chief_narrative" in df.columns:
    df = df.withColumn(
        "chief_narrative",
        F.regexp_replace(F.col("chief_narrative"), "<[^>]+>", ""),
    )

df = df.withColumn("extracted_at", F.current_timestamp())

logger.info(f"Cleaned record count: {df.count()}")

# ---------------------------------------------------------------------------
# Load — upsert into Redshift
# ---------------------------------------------------------------------------

dyf = DynamicFrame.fromDF(df, glueContext, "narratives_clean")

pre_actions = """
    CREATE TEMP TABLE stg_narratives (LIKE catt.narratives);
"""
post_actions = """
    DELETE FROM catt.narratives
    USING stg_narratives
    WHERE catt.narratives.id = stg_narratives.id;

    INSERT INTO catt.narratives
    SELECT * FROM stg_narratives;

    DROP TABLE stg_narratives;
"""

glueContext.write_dynamic_frame.from_jdbc_conf(
    frame=dyf,
    catalog_connection=args["REDSHIFT_CONNECTION"],
    connection_options={
        "database": "dev",
        "dbtable": "stg_narratives",
        "preactions": pre_actions,
        "postactions": post_actions,
    },
    redshift_tmp_dir=f"{s3_path}tmp/narratives/",
)

logger.info("Narratives upsert complete")
job.commit()
