ALTER TABLE users
ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'USER';

ALTER TABLE users
ADD CONSTRAINT users_role_check
CHECK (role IN ('USER', 'ADMIN', 'FOUNDER'));

CREATE INDEX users_role_idx
ON users(role);

UPDATE users
SET
    role = 'FOUNDER',
    updated_at = NOW()
WHERE LOWER(email) = LOWER('leonwillamowski@gmail.com');
