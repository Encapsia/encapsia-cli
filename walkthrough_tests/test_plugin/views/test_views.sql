-- A selection of example functions, illustrating the different ways to accept arguments.

-- No arguments.
-- GET v1/views/example/test_no_args
DROP FUNCTION IF EXISTS test_no_args();
CREATE OR REPLACE FUNCTION test_no_args()
RETURNS TABLE(answer TEXT) AS
$$
SELECT 'function with no arguments'::TEXT AS answer;
$$
LANGUAGE sql;


-- One required argument.
-- GET v1/views/example/test_one_arg/<foo>
DROP FUNCTION IF EXISTS test_one_arg(arg1 TEXT);
CREATE OR REPLACE FUNCTION test_one_arg(arg1 TEXT)
RETURNS TABLE(argument TEXT) AS
$$
SELECT arg1 AS argument;
$$
LANGUAGE sql;


-- Two required arguments.
-- GET v1/views/example/test_two_args/arg1/arg2
CREATE OR REPLACE FUNCTION test_two_args(arg1 TEXT, arg2 TEXT)
RETURNS TEXT AS
$$
SELECT arg1 || arg2;
$$
LANGUAGE sql;


-- Accept meta information.
-- GET v1/views/example/test_only_meta
CREATE OR REPLACE FUNCTION test_only_meta("meta" JSON DEFAULT NULL)
RETURNS JSON AS
$$
SELECT meta
$$
LANGUAGE sql;


-- One optional argument.
-- GET v1/views/example/test_one_optional_arg
-- GET v1/views/example/test_one_optional_arg?limit=100
CREATE OR REPLACE FUNCTION test_one_optional_arg("limit" INTEGER DEFAULT 1000)
RETURNS INTEGER AS
$$
SELECT "limit"
$$
LANGUAGE sql;


-- Mixture of fixed and optional args, with meta.
-- GET v1/views/example/test_mixture/an_arg1?limit=999
CREATE OR REPLACE FUNCTION test_mixture(arg1 TEXT, "limit" INT DEFAULT 1000, "meta" JSON DEFAULT NULL)
RETURNS JSONB AS
$$
SELECT jsonb_build_object('arg1', arg1, 'limit', "limit", 'meta', "meta");
$$
LANGUAGE sql;


-- Return CSV data directly.
-- POST v1/views/example/example_view_function_as_csv_file
CREATE OR REPLACE FUNCTION example_view_function_as_csv_file(
    output_filename TEXT DEFAULT NULL,
    meta JSONB DEFAULT NULL,
    OUT result operational.result_as_csv_file
) AS $$
BEGIN
    CREATE TEMPORARY VIEW temp AS SELECT * FROM (VALUES (1,2), (3,4)) AS test_data (x, y);
    SELECT operational.write_to_csv('temp', output_filename) INTO result;
    DROP VIEW temp;
END;
$$ LANGUAGE plpgsql;


-- Upload data in POST body as CSV, e.g.
-- curl -H "Authorization: Bearer $ENCAPSIA_TOKEN" \
--   -H "Accept: application/json" \
--   -H "Content-type: text/csv" \
--   $ENCAPSIA_URL/v1/views/example/example_create_and_populate_table \
--   -X POST --data-binary @/path/to/foo.csv
-- where file.csv is a headerless CSV like:
--   Treaty of Paris, 1951
--   Treaty of Rome, 1957
--   Merger Treaty, 1967
--   Maastricht Treaty, 1992
DROP FUNCTION IF EXISTS example_create_and_populate_table(TEXT, TEXT, JSONB);
CREATE OR REPLACE FUNCTION example_create_and_populate_table(
    raw_data_filename TEXT DEFAULT NULL,
    raw_data_type TEXT DEFAULT NULL,
    meta JSONB DEFAULT NULL
) RETURNS TABLE(n_records BIGINT) AS
$$
BEGIN
    DROP TABLE IF EXISTS example_uploaded_table;
    CREATE TABLE example_uploaded_table(col2 INTEGER, col1 TEXT);
    PERFORM read_from_csv(
         'example_uploaded_table'
        ,raw_data_filename
        ,columns => ARRAY['col1', 'col2']
        ,header => false
        ,quote_char => '"'
        ,delimiter_char => ','
        ,escape_char => '"'
        ,null_string => ''
        ,force_null => ARRAY['col1']
    );
    --If uploading large amounts of data, might want to
    --ANALYZE example_uploaded_table;

    -- We may as well return something informative...
    RETURN QUERY (SELECT count(*) AS n_records FROM example_uploaded_table);
END;
$$ LANGUAGE plpgsql;

-- Overloaded signature.
-- GET v1/views/example/test_overloaded
DROP FUNCTION IF EXISTS test_overloaded();
CREATE OR REPLACE FUNCTION test_one_arg()
RETURNS TABLE(argument TEXT) AS
$$
SELECT 'overloaded' AS argument;
$$
LANGUAGE sql;

-- Same name but with one argument this time
-- GET v1/views/example/test_overloaded/foo
DROP FUNCTION IF EXISTS test_overloaded(arg1 TEXT);
CREATE OR REPLACE FUNCTION test_one_arg(arg1 TEXT)
RETURNS TABLE(argument TEXT) AS
$$
SELECT arg1 AS argument;
$$
LANGUAGE sql;
