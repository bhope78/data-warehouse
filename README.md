# CATT Data Warehouse

ETL pipeline that extracts data from SharePoint Lists (Microsoft Graph API), stages in S3, transforms with AWS Glue, and loads into Amazon Redshift Serverless for Power BI reporting.

## Architecture

```
┌──────────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  SharePoint Online   │     │    Amazon S3      │     │    AWS Glue      │     │    Redshift      │
│  (Graph API)         │────▶│  (Raw JSON)       │────▶│  (PySpark ETL)   │────▶│  Serverless      │
│                      │     │                   │     │                  │     │                  │
│  • Episodes List     │     │  catt-pipeline/   │     │  • Clean nulls   │     │  catt.episodes   │
│  • CATT Time List    │     │    raw/YYYY-MM-DD │     │  • Cast types    │     │  catt.catt_times │
│  • Narrative List    │     │    /episodes.json  │     │  • snake_case    │     │  catt.narratives │
│                      │     │    /catt-times.json│     │  • Upsert merge  │     │                  │
│                      │     │    /narratives.json│     │                  │     │                  │
└──────────────────────┘     └──────────────────┘     └──────────────────┘     └─────────┬────────┘
                                                                                        │
                                                                                        ▼
                                                                               ┌──────────────────┐
                                                                               │   Power BI       │
                                                                               │   Desktop        │
                                                                               │   (ODBC/DirectQ) │
                                                                               └──────────────────┘
```

## Project Structure

```
├── src/
│   └── sharepoint-extractor.js   # Node.js — Graph API → S3
├── glue/
│   ├── transform-episodes.py     # Glue ETL — episodes
│   ├── transform-catt-times.py   # Glue ETL — CATT times
│   └── transform-narratives.py   # Glue ETL — narratives
├── redshift/
│   └── schema.sql                # DDL for catt schema + tables
├── scripts/
│   └── setup-aws.sh              # Automated AWS infrastructure setup
├── .env.example                  # Required environment variables
└── package.json
```

## Prerequisites

### Azure AD App Registration
1. Register an app in [Azure Entra ID](https://entra.microsoft.com)
2. Grant **Application** permission: `Sites.Read.All` (Microsoft Graph)
3. Grant admin consent for the tenant
4. Create a client secret
5. Note your `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, and `AZURE_CLIENT_SECRET`

### AWS
- AWS CLI v2 configured with admin-level access
- Default region: `us-west-2` (configurable via `AWS_REGION`)

## Setup & Deployment

### 1. Install dependencies

```bash
npm install
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in all required values — see .env.example for descriptions
```

### 3. Provision AWS infrastructure

```bash
bash scripts/setup-aws.sh
```

This creates:
- S3 bucket for raw data and Glue scripts
- IAM role for Glue with S3 + Redshift access
- Redshift Serverless namespace + workgroup (8 RPU base capacity)
- Three Glue ETL jobs with daily triggers (7:00 UTC)
- Glue JDBC connection to Redshift

### 4. Create Redshift schema

Connect to Redshift via the AWS Console Query Editor v2 or psql and run:

```sql
-- Run the contents of redshift/schema.sql
\i redshift/schema.sql
```

### 5. Run the extractor

```bash
# Dry run — fetches data but does not upload to S3
npm run extract:dry-run

# Full extraction — uploads JSON to S3
npm run extract
```

### 6. Run Glue jobs

Jobs run daily at 7:00 UTC automatically. To trigger manually:

```bash
aws glue start-job-run --job-name catt-transform-episodes
aws glue start-job-run --job-name catt-transform-catt-times
aws glue start-job-run --job-name catt-transform-narratives
```

## Scheduling the Extractor

The extractor should run before the Glue triggers (which fire at 7:00 UTC):

```bash
# Example crontab entry — daily at 6:00 UTC
0 6 * * * cd /path/to/data-warehouse && node src/sharepoint-extractor.js >> /var/log/catt-extract.log 2>&1
```

## Connecting Power BI to Redshift

### Install the ODBC Driver
Download the [Amazon Redshift ODBC driver](https://docs.aws.amazon.com/redshift/latest/mgmt/install-odbc-driver-windows.html)

### Connect from Power BI Desktop
1. **Get Data** → **Amazon Redshift**
2. **Server**: `<workgroup>.<account-id>.<region>.redshift-serverless.amazonaws.com:5439`
3. **Database**: `dev`
4. **Data Connectivity mode**: DirectQuery (recommended) or Import
5. **Credentials**: Redshift admin user (password stored in AWS Secrets Manager)
6. Select tables from the `catt` schema

### ODBC Connection String

```
Driver={Amazon Redshift ODBC Driver (x64)};
Server=<your-workgroup>.<your-account-id>.<your-region>.redshift-serverless.amazonaws.com;
Port=5439;
Database=dev;
UID=<admin-username>;
PWD=<password-from-secrets-manager>;
```

## Data Sources

| List | Description | Schedule |
|------|-------------|----------|
| Episodes List | Incident-level clinical + demographic data | Daily |
| CATT Time List | Response time milestones from ESO | Daily |
| Narrative List | Clinical narratives + chief complaints | Daily |

## Security Notes

- All credentials are loaded from environment variables — never commit `.env`
- Redshift admin password is managed by AWS Secrets Manager
- The SharePoint site ID and list IDs are resolved dynamically at runtime from `SHAREPOINT_SITE_URL`
- The Glue connection password should reference Secrets Manager in production
