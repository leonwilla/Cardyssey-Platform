ALTER TABLE users
ADD COLUMN friend_code TEXT;

UPDATE users
SET friend_code =
    'CDY-' ||
    UPPER(SUBSTRING(REPLACE(id::text, '-', '') FROM 1 FOR 4)) || '-' ||
    UPPER(SUBSTRING(REPLACE(id::text, '-', '') FROM 5 FOR 4)) || '-' ||
    UPPER(SUBSTRING(REPLACE(id::text, '-', '') FROM 9 FOR 4)) || '-' ||
    UPPER(SUBSTRING(REPLACE(id::text, '-', '') FROM 13 FOR 4)) || '-' ||
    UPPER(SUBSTRING(REPLACE(id::text, '-', '') FROM 17 FOR 4));

ALTER TABLE users
ALTER COLUMN friend_code SET NOT NULL;

ALTER TABLE users
ADD CONSTRAINT users_friend_code_unique
UNIQUE (friend_code);
