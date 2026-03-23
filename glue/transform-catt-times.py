"""
Glue ETL — CATT Time List → catt.catt_times

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
logger.info(f"Reading catt-times from {s3_path}catt-times.json")

df = spark.read.json(f"{s3_path}catt-times.json")
logger.info(f"Raw record count: {df.count()}")

# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------

COLUMN_MAP = {
    "id": "id",
    "Title": "title",
    "IncidentNumber": "incident_number",
    "IncidentDate": "incident_date",
    "Disposition": "disposition",
    "Unit": "unit",
    "CrewMemberFirstName": "crew_member_first_name",
    "CrewMemberLastName": "crew_member_last_name",
    "CrewMemberRole": "crew_member_role",
    "CrewMemberId": "crew_member_id",
    "CallReceivedTime": "call_received_time",
    "DispatchNotifiedTime": "dispatch_notified_time",
    "DispatchedTime": "dispatched_time",
    "EnRouteTime": "en_route_time",
    "InitialResponderArrivedTime": "initial_responder_arrived_time",
    "On_x0020_Scene_x0020_Time": "on_scene_time",
    "At_x0020_Patient_x0020_Time": "at_patient_time",
    "DepartSceneTime": "depart_scene_time",
    "AtDestinationTime": "at_destination_time",
    "IncidentClosedTime": "incident_closed_time",
    "UnitBackatHomeTime": "unit_back_at_home_time",
    "Involuntary_x0020_Hold_x0020_Tim": "involuntary_hold_time",
    "OpenTime": "open_time",
    "CloseTime": "close_time",
    "OpeningSubmitTime": "opening_submit_time",
    "ClosingSubmitTime": "closing_submit_time",
    "ClosingSubmitted": "closing_submitted",
    "SceneCity": "scene_city",
    "SceneZip": "scene_zip",
    "Is_x0020_Lock": "is_lock",
    "IsActive": "is_active",
    "Source": "source",
    "SyncDate": "sync_date",
    "LockDate": "lock_date",
    "CreatedTime": "created_time",
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

# Cast dates
if "incident_date" in df.columns:
    df = df.withColumn("incident_date", F.to_date(F.col("incident_date")))

# Cast all timestamp columns
ts_cols = [
    "call_received_time", "dispatch_notified_time", "dispatched_time",
    "en_route_time", "initial_responder_arrived_time", "on_scene_time",
    "at_patient_time", "depart_scene_time", "at_destination_time",
    "incident_closed_time", "unit_back_at_home_time", "involuntary_hold_time",
    "open_time", "close_time", "opening_submit_time", "closing_submit_time",
    "sync_date", "lock_date", "created_time", "sp_created", "sp_modified",
]
for col_name in ts_cols:
    if col_name in df.columns:
        df = df.withColumn(col_name, F.to_timestamp(F.col(col_name)))

if "id" in df.columns:
    df = df.withColumn("id", F.col("id").cast(IntegerType()))

df = df.withColumn("extracted_at", F.current_timestamp())

logger.info(f"Cleaned record count: {df.count()}")

# ---------------------------------------------------------------------------
# Load — upsert into Redshift
# ---------------------------------------------------------------------------

dyf = DynamicFrame.fromDF(df, glueContext, "catt_times_clean")

pre_actions = """
    CREATE TEMP TABLE stg_catt_times (LIKE catt.catt_times);
"""
post_actions = """
    DELETE FROM catt.catt_times
    USING stg_catt_times
    WHERE catt.catt_times.id = stg_catt_times.id;

    INSERT INTO catt.catt_times
    SELECT * FROM stg_catt_times;

    DROP TABLE stg_catt_times;
"""

glueContext.write_dynamic_frame.from_jdbc_conf(
    frame=dyf,
    catalog_connection=args["REDSHIFT_CONNECTION"],
    connection_options={
        "database": "dev",
        "dbtable": "stg_catt_times",
        "preactions": pre_actions,
        "postactions": post_actions,
    },
    redshift_tmp_dir=f"{s3_path}tmp/catt-times/",
)

logger.info("CATT Times upsert complete")
job.commit()
