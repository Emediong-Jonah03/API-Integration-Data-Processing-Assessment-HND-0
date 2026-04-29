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

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE users (
    id TEXT PRIMARY KEY, -- UUID v7 as string
    github_id VARCHAR UNIQUE NOT NULL,
    username VARCHAR,
    email VARCHAR,
    avatar_url VARCHAR,
    role VARCHAR DEFAULT 'analyst',
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid (),
    user_id TEXT REFERENCES users (id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);