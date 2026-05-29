-- 1. Create a new user if it doesn't exist (or just reset password)
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_user
      WHERE  usename = 'nexus') THEN

      CREATE USER nexus WITH PASSWORD 'PinkFloyd';
   ELSE
      ALTER USER nexus WITH PASSWORD 'PinkFloyd';
   END IF;
END
$do$;

-- 2. Create the database if it doesn't exist
SELECT 'CREATE DATABASE nexus_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'nexus_db')\gexec

-- 3. Grant privileges
GRANT ALL PRIVILEGES ON DATABASE nexus_db TO nexus;
ALTER DATABASE nexus_db OWNER TO nexus;
