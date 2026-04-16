CREATE TABLE profiles (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    name TEXT NOT NULL UNIQUE,
    gender TEXT,
    gender_probability DOUBLE PRECISION,
    sample_size INTEGER,
    age INTEGER,
    age_group TEXT,
    country_id TEXT,
    country_probability DOUBLE PRECISION
);