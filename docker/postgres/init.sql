-- Create schemas for the data warehouse layers
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS marts;

-- Grant usage
GRANT USAGE ON SCHEMA raw TO postgres;
GRANT USAGE ON SCHEMA staging TO postgres;
GRANT USAGE ON SCHEMA marts TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA raw TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA staging TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA marts TO postgres;
