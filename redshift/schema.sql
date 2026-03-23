-- ==========================================================================
-- CATT Data Warehouse — Redshift Serverless Schema
-- ==========================================================================

CREATE SCHEMA IF NOT EXISTS catt;

-- --------------------------------------------------------------------------
-- catt.episodes
-- One row per crew-member per incident. Primary analytical table.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS catt.episodes (
    id                              INTEGER         ENCODE az64,
    title                           VARCHAR(255)    ENCODE zstd,
    incident_number                 VARCHAR(255)    ENCODE zstd,
    incident_date                   DATE            ENCODE az64,
    disposition                     VARCHAR(255)    ENCODE zstd,
    unit_call_sign                  VARCHAR(100)    ENCODE zstd,

    -- Crew
    crew_first_name                 VARCHAR(255)    ENCODE zstd,
    crew_last_name                  VARCHAR(255)    ENCODE zstd,
    crew_member_role                VARCHAR(100)    ENCODE zstd,
    crew_member_id                  VARCHAR(100)    ENCODE zstd,
    crew_member_level               VARCHAR(100)    ENCODE zstd,

    -- Timestamps (string from ESO, cast in transform)
    call_received_time              TIMESTAMP       ENCODE az64,
    dispatched_time                 TIMESTAMP       ENCODE az64,
    en_route_time                   TIMESTAMP       ENCODE az64,
    on_scene_time                   TIMESTAMP       ENCODE az64,
    at_patient_time                 TIMESTAMP       ENCODE az64,
    depart_scene_time               TIMESTAMP       ENCODE az64,
    at_destination_time             TIMESTAMP       ENCODE az64,
    incident_closed_time            TIMESTAMP       ENCODE az64,

    -- Durations (seconds)
    call_received_time_seconds      BIGINT          ENCODE az64,
    dispatched_time_seconds         BIGINT          ENCODE az64,
    en_route_time_seconds           BIGINT          ENCODE az64,
    on_scene_time_seconds           BIGINT          ENCODE az64,
    at_patient_time_seconds         BIGINT          ENCODE az64,
    depart_scene_time_seconds       BIGINT          ENCODE az64,
    at_destination_time_seconds     BIGINT          ENCODE az64,
    incident_closed_time_seconds    BIGINT          ENCODE az64,

    -- Transport / Location
    transported_to_destination      VARCHAR(500)    ENCODE zstd,
    location_type                   VARCHAR(255)    ENCODE zstd,
    location_name                   VARCHAR(500)    ENCODE zstd,
    scene_address1                  VARCHAR(500)    ENCODE zstd,
    scene_address2                  VARCHAR(500)    ENCODE zstd,
    scene_city                      VARCHAR(255)    ENCODE zstd,
    scene_state                     VARCHAR(50)     ENCODE zstd,
    scene_county                    VARCHAR(255)    ENCODE zstd,
    scene_zip_code                  VARCHAR(20)     ENCODE zstd,
    scene_latitude                  DECIMAL(10,7)   ENCODE az64,
    scene_longitude                 DECIMAL(10,7)   ENCODE az64,

    -- Patient demographics
    race                            VARCHAR(255)    ENCODE zstd,
    patient_dob                     DATE            ENCODE az64,
    patient_age                     VARCHAR(20)     ENCODE zstd,
    gender                          VARCHAR(50)     ENCODE zstd,
    ethnicity                       VARCHAR(255)    ENCODE zstd,

    -- Insurance
    primary_payer                   VARCHAR(255)    ENCODE zstd,
    primary_insurance_company       VARCHAR(500)    ENCODE zstd,
    primary_policy_number           VARCHAR(255)    ENCODE zstd,

    -- Clinical
    chief_complaint                 VARCHAR(500)    ENCODE zstd,
    chief_narrative                 VARCHAR(MAX)    ENCODE zstd,
    primary_diagnosis               VARCHAR(500)    ENCODE zstd,
    primary_diagnosis_code          VARCHAR(50)     ENCODE zstd,
    secondary_diagnosis             VARCHAR(500)    ENCODE zstd,

    -- Episode lifecycle
    status                          VARCHAR(100)    ENCODE zstd,
    is_active                       VARCHAR(10)     ENCODE zstd,
    source                          VARCHAR(100)    ENCODE zstd,
    welligent_id                    VARCHAR(100)    ENCODE zstd,
    client_number                   VARCHAR(100)    ENCODE zstd,
    service_number                  VARCHAR(100)    ENCODE zstd,

    -- Metadata
    sp_created                      TIMESTAMP       ENCODE az64,
    sp_modified                     TIMESTAMP       ENCODE az64,
    extracted_at                    TIMESTAMP       DEFAULT GETDATE() ENCODE az64,

    PRIMARY KEY (id)
)
DISTKEY (incident_number)
SORTKEY (incident_date);


-- --------------------------------------------------------------------------
-- catt.catt_times
-- Response time records synced from ESO.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS catt.catt_times (
    id                              INTEGER         ENCODE az64,
    title                           VARCHAR(255)    ENCODE zstd,
    incident_number                 VARCHAR(255)    ENCODE zstd,
    incident_date                   DATE            ENCODE az64,
    disposition                     VARCHAR(255)    ENCODE zstd,
    unit                            VARCHAR(100)    ENCODE zstd,

    -- Crew
    crew_member_first_name          VARCHAR(255)    ENCODE zstd,
    crew_member_last_name           VARCHAR(255)    ENCODE zstd,
    crew_member_role                VARCHAR(100)    ENCODE zstd,
    crew_member_id                  VARCHAR(100)    ENCODE zstd,

    -- Time milestones
    call_received_time              TIMESTAMP       ENCODE az64,
    dispatch_notified_time          TIMESTAMP       ENCODE az64,
    dispatched_time                 TIMESTAMP       ENCODE az64,
    en_route_time                   TIMESTAMP       ENCODE az64,
    initial_responder_arrived_time  TIMESTAMP       ENCODE az64,
    on_scene_time                   TIMESTAMP       ENCODE az64,
    at_patient_time                 TIMESTAMP       ENCODE az64,
    depart_scene_time               TIMESTAMP       ENCODE az64,
    at_destination_time             TIMESTAMP       ENCODE az64,
    incident_closed_time            TIMESTAMP       ENCODE az64,
    unit_back_at_home_time          TIMESTAMP       ENCODE az64,
    involuntary_hold_time           TIMESTAMP       ENCODE az64,

    -- Open/Close lifecycle
    open_time                       TIMESTAMP       ENCODE az64,
    close_time                      TIMESTAMP       ENCODE az64,
    opening_submit_time             TIMESTAMP       ENCODE az64,
    closing_submit_time             TIMESTAMP       ENCODE az64,
    closing_submitted               VARCHAR(10)     ENCODE zstd,

    -- Location
    scene_city                      VARCHAR(255)    ENCODE zstd,
    scene_zip                       VARCHAR(20)     ENCODE zstd,

    -- Flags
    is_lock                         VARCHAR(10)     ENCODE zstd,
    is_active                       VARCHAR(10)     ENCODE zstd,
    source                          VARCHAR(100)    ENCODE zstd,

    -- Sync metadata
    sync_date                       TIMESTAMP       ENCODE az64,
    lock_date                       TIMESTAMP       ENCODE az64,
    created_time                    TIMESTAMP       ENCODE az64,
    sp_created                      TIMESTAMP       ENCODE az64,
    sp_modified                     TIMESTAMP       ENCODE az64,
    extracted_at                    TIMESTAMP       DEFAULT GETDATE() ENCODE az64,

    PRIMARY KEY (id)
)
DISTKEY (incident_number)
SORTKEY (incident_date);


-- --------------------------------------------------------------------------
-- catt.narratives
-- Clinical narratives per incident.
-- --------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS catt.narratives (
    id                              INTEGER         ENCODE az64,
    title                           VARCHAR(255)    ENCODE zstd,
    incident_number                 VARCHAR(255)    ENCODE zstd,
    run_number                      VARCHAR(255)    ENCODE zstd,
    incident_date                   DATE            ENCODE az64,
    disposition                     VARCHAR(255)    ENCODE zstd,
    chief_complaint                 VARCHAR(500)    ENCODE zstd,
    chief_narrative                 VARCHAR(MAX)    ENCODE zstd,
    client_profile                  VARCHAR(500)    ENCODE zstd,
    housing_stability               VARCHAR(50)     ENCODE zstd,

    -- Crew
    crew_first_name                 VARCHAR(255)    ENCODE zstd,
    crew_last_name                  VARCHAR(255)    ENCODE zstd,
    crew_member_level               VARCHAR(100)    ENCODE zstd,

    -- Flags
    is_lock                         VARCHAR(10)     ENCODE zstd,
    pd_call_out_reason              VARCHAR(500)    ENCODE zstd,
    source                          VARCHAR(100)    ENCODE zstd,

    -- Metadata
    sp_created                      TIMESTAMP       ENCODE az64,
    sp_modified                     TIMESTAMP       ENCODE az64,
    extracted_at                    TIMESTAMP       DEFAULT GETDATE() ENCODE az64,

    PRIMARY KEY (id)
)
DISTKEY (incident_number)
SORTKEY (incident_date);
