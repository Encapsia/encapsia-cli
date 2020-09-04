DROP TABLE IF EXISTS static_permissions;
CREATE TABLE static_permissions (
  name          TEXT PRIMARY KEY,
  description   TEXT NOT NULL,
  display_name  TEXT NOT NULL,
  capabilities  TEXT []
);

INSERT INTO static_permissions(name, display_name, description, capabilities)
VALUES
(
  'example',
  'Example',
  'Permission for the "example" plugin.',
  ARRAY[
    'task.run.example'
  ]
);

DROP FUNCTION IF EXISTS permissions();
CREATE OR REPLACE FUNCTION permissions()
RETURNS TABLE (
  name TEXT,
  description TEXT,
  display_name TEXT,
  capabilities TEXT[]
)
AS
$$
SELECT * FROM static_permissions;
$$ LANGUAGE SQL;