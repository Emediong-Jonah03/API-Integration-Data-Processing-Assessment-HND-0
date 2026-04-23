CREATE TABLE profiles (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    gender VARCHAR NOT NULL CHECK (gender IN ('male', 'female')),
    gender_probability FLOAT NOT NULL CHECK (
        gender_probability BETWEEN 0 AND 1
    ),
    age INTEGER NOT NULL CHECK (age >= 0),
    age_group VARCHAR NOT NULL,
    country_id VARCHAR(2) NOT NULL,
    country_name VARCHAR NOT NULL,
    country_probability FLOAT NOT NULL CHECK (
        country_probability BETWEEN 0 AND 1
    ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);