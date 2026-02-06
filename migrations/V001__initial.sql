CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    is_verified_seller BOOLEAN NOT NULL
);


CREATE TABLE items (
    id SERIAL PRIMARY KEY,
    seller_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    category INTEGER NOT NULL,
    images_qty INTEGER NOT NULL
);
