CREATE EXTENSION IF NOT EXISTS pgcrypto;

INSERT INTO profiles (
    id,
    name,
    gender,
    gender_probability,
    age,
    age_group,
    country_id,
    country_name,
    country_probability
)
SELECT
    gen_random_uuid(),
    p.name,
    p.gender,
    p.gender_probability,
    p.age,
    p.age_group,
    p.country_id,
    p.country_name,
    p.country_probability
FROM jsonb_to_recordset(
    pg_read_file('seed_profiles.json')::jsonb -> 'profiles'
) AS p(
    name VARCHAR(255),
    gender VARCHAR(10),
    gender_probability FLOAT,
    age INTEGER,
    age_group VARCHAR(20),
    country_id CHAR(2),
    country_name VARCHAR(100),
    country_probability FLOAT
)
ON CONFLICT (name) DO NOTHING;