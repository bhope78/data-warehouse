"""
Glue ETL — Episodes List → catt.episodes

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
from pyspark.sql.types import DateType, TimestampType, DecimalType, IntegerType, LongType

args = getResolvedOptions(sys.argv, ["JOB_NAME", "S3_RAW_PATH", "REDSHIFT_CONNECTION"])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

logger = glueContext.get_logger()

# ---------------------------------------------------------------------------
# Extract — read raw JSON from S3
# ---------------------------------------------------------------------------

s3_path = args["S3_RAW_PATH"]  # e.g. s3://catt-pipeline-data/catt-pipeline/raw/2026-03-23/
logger.info(f"Reading episodes from {s3_path}episodes.json")

df = spark.read.json(f"{s3_path}episodes.json")
logger.info(f"Raw record count: {df.count()}")

# ---------------------------------------------------------------------------
# Transform — clean and standardize
# ---------------------------------------------------------------------------

# Column mapping: SharePoint field name → snake_case Redshift column
COLUMN_MAP = {
    "id": "id",
    "Title": "title",
    "IncidentDate": "incident_date",
    "Disposition": "disposition",
    "UnitCallSign": "unit_call_sign",
    "CrewFirstName": "crew_first_name",
    "CrewLastName": "crew_last_name",
    "CrewMemberRole": "crew_member_role",
    "CrewMemberID": "crew_member_id",
    "CrewMemberLevel": "crew_member_level",
    "CallReceivedTime": "call_received_time",
    "DispatchedTime": "dispatched_time",
    "EnRouteTime": "en_route_time",
    "OnSceneTime": "on_scene_time",
    "AtPatientTime": "at_patient_time",
    "DepartSceneTime": "depart_scene_time",
    "AtDestinationTime": "at_destination_time",
    "IncidentClosedTime": "incident_closed_time",
    "CallReceivedTimeInSecond": "call_received_time_seconds",
    "DispatchedTimeInSecond": "dispatched_time_seconds",
    "EnRouteTimeInSecond": "en_route_time_seconds",
    "OnSceneTimeInSecond": "on_scene_time_seconds",
    "AtPatientTimeInSecond": "at_patient_time_seconds",
    "DepartSceneTimeInSecond": "depart_scene_time_seconds",
    "AtDestinationTimeInSecond": "at_destination_time_seconds",
    "IncidentClosedTimeInSecond": "incident_closed_time_seconds",
    "TransportedToDestination": "transported_to_destination",
    "LocationType": "location_type",
    "LocationName": "location_name",
    "SceneAddress1": "scene_address1",
    "SceneAddress2": "scene_address2",
    "SceneCity": "scene_city",
    "SceneState": "scene_state",
    "SceneCounty": "scene_county",
    "SceneZIPCode": "scene_zip_code",
    "SceneGPSLocationLatitude": "scene_latitude",
    "SceneGPSLocationLongitude": "scene_longitude",
    "Race": "race",
    "PatientDOB": "patient_dob",
    "PatientAge": "patient_age",
    "Gender": "gender",
    "Ethnicity": "ethnicity",
    "PrimaryPayer": "primary_payer",
    "PrimaryInsuranceCompanyName": "primary_insurance_company",
    "PrimaryPolicyNumber": "primary_policy_number",
    "ChiefComplaint": "chief_complaint",
    "ChiefNarrative": "chief_narrative",
    "PrimaryDiagnosis": "primary_diagnosis",
    "PrimaryDiagnosisCode": "primary_diagnosis_code",
    "SecondaryDiagnosis": "secondary_diagnosis",
    "Status": "status",
    "IsActive": "is_active",
    "Source": "source",
    "WelligentID": "welligent_id",
    "ClientNumber": "client_number",
    "ServiceNumber": "service_number",
    "NewIncidentNumber": "incident_number",
    "Created": "sp_created",
    "Modified": "sp_modified",
}

# Select and rename columns (skip any that don't exist in this extract)
existing_cols = set(df.columns)
select_exprs = []
for sp_col, rs_col in COLUMN_MAP.items():
    if sp_col in existing_cols:
        select_exprs.append(F.col(sp_col).alias(rs_col))

df = df.select(select_exprs)

# If incident_number is null, fall back to title (which is typically the incident number)
if "incident_number" in df.columns:
    df = df.withColumn(
        "incident_number",
        F.coalesce(F.col("incident_number"), F.col("title")),
    )

# Cast types
date_cols = ["incident_date", "patient_dob"]
ts_cols = [
    "call_received_time", "dispatched_time", "en_route_time", "on_scene_time",
    "at_patient_time", "depart_scene_time", "at_destination_time",
    "incident_closed_time", "sp_created", "sp_modified",
]
long_cols = [c for c in df.columns if c.endswith("_seconds")]
decimal_cols = ["scene_latitude", "scene_longitude"]

for col_name in date_cols:
    if col_name in df.columns:
        df = df.withColumn(col_name, F.to_date(F.col(col_name)))

for col_name in ts_cols:
    if col_name in df.columns:
        df = df.withColumn(col_name, F.to_timestamp(F.col(col_name)))

for col_name in long_cols:
    if col_name in df.columns:
        df = df.withColumn(col_name, F.col(col_name).cast(LongType()))

for col_name in decimal_cols:
    if col_name in df.columns:
        df = df.withColumn(col_name, F.col(col_name).cast(DecimalType(10, 7)))

if "id" in df.columns:
    df = df.withColumn("id", F.col("id").cast(IntegerType()))

# Drop rows with no incident identifier
df = df.filter(F.col("incident_number").isNotNull() | F.col("title").isNotNull())

# Add extraction timestamp
df = df.withColumn("extracted_at", F.current_timestamp())

logger.info(f"Cleaned record count: {df.count()}")

# ---------------------------------------------------------------------------
# Load — upsert into Redshift via staging table
# ---------------------------------------------------------------------------

dyf = DynamicFrame.fromDF(df, glueContext, "episodes_clean")

# Write to a Redshift staging table, then merge
pre_actions = """
    CREATE TEMP TABLE stg_episodes (LIKE catt.episodes);
"""
post_actions = """
    DELETE FROM catt.episodes
    USING stg_episodes
    WHERE catt.episodes.id = stg_episodes.id;

    INSERT INTO catt.episodes
    SELECT * FROM stg_episodes;

    DROP TABLE stg_episodes;
"""

glueContext.write_dynamic_frame.from_jdbc_conf(
    frame=dyf,
    catalog_connection=args["REDSHIFT_CONNECTION"],
    connection_options={
        "database": "dev",
        "dbtable": "stg_episodes",
        "preactions": pre_actions,
        "postactions": post_actions,
    },
    redshift_tmp_dir=f"{s3_path}tmp/episodes/",
)

logger.info("Episodes upsert complete")
job.commit()
