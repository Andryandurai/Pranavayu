from django.db import migrations


def hypertable_sql(table, partition_column):
    return f"""
        SELECT create_hypertable(
            '{table}', '{partition_column}',
            chunk_time_interval => INTERVAL '7 days',
            if_not_exists => TRUE, migrate_data => TRUE
        );
    """


def regular_table_sql(table):
    # Timescale has no supported in-place inverse of create_hypertable. Rebuild
    # the ordinary table in this transaction, retaining rows, keys and indexes.
    # No project model may reference these composite-key tables with an FK.
    return f"""
        DO $reverse_hypertable$
        DECLARE
            restore_constraints text[];
            restore_indexes text[];
            ddl text;
        BEGIN
            LOCK TABLE {table} IN ACCESS EXCLUSIVE MODE;
            SELECT array_agg(format('ALTER TABLE {table} ADD CONSTRAINT %I %s',
                                   conname, pg_get_constraintdef(oid)))
                INTO restore_constraints
                FROM pg_constraint
                WHERE conrelid = '{table}'::regclass AND contype IN ('p', 'u', 'f', 'x');
            SELECT array_agg(pg_get_indexdef(indexrelid))
                INTO restore_indexes
                FROM pg_index i
                WHERE indrelid = '{table}'::regclass
                  AND NOT EXISTS (SELECT 1 FROM pg_constraint c WHERE c.conindid = i.indexrelid);
            CREATE TABLE {table}_regular
                (LIKE {table} INCLUDING DEFAULTS INCLUDING CONSTRAINTS
                              INCLUDING GENERATED INCLUDING STORAGE);
            INSERT INTO {table}_regular SELECT * FROM {table};
            DROP TABLE {table};
            ALTER TABLE {table}_regular RENAME TO {table};
            FOREACH ddl IN ARRAY coalesce(restore_constraints, ARRAY[]::text[]) LOOP
                EXECUTE ddl;
            END LOOP;
            FOREACH ddl IN ARRAY coalesce(restore_indexes, ARRAY[]::text[]) LOOP
                EXECUTE ddl;
            END LOOP;
        END
        $reverse_hypertable$;
    """


class Migration(migrations.Migration):
    dependencies = [("warehouse", "0001_initial")]
    operations = [
        migrations.RunSQL(
            hypertable_sql("warehouse_reading", "observed_at"),
            regular_table_sql("warehouse_reading"),
        ),
        migrations.RunSQL(
            hypertable_sql("warehouse_weatherobservation", "observed_at"),
            regular_table_sql("warehouse_weatherobservation"),
        ),
        migrations.RunSQL(
            hypertable_sql("warehouse_firedetection", "detected_at"),
            regular_table_sql("warehouse_firedetection"),
        ),
    ]
