CREATE TABLE account (
    id SERIAL PRIMARY KEY,
    login TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    is_blocked BOOL DEFAULT FALSE
);
