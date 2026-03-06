#!/usr/bin/env python3
"""STAC GeoParquet Exporter - Direct execution script"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from stac_geoparquet.pgstac_reader import pgstac_to_parquet, sync_pgstac_to_parquet


def main():
    mode = os.environ.get("EXPORT_MODE", "incremental")
    config_path = os.environ.get("CONFIG_PATH", "/config/export-config.yaml")
    output_base = os.environ.get("OUTPUT_PATH", "/output")

    # Build PostgreSQL connection string
    conninfo = (
        f"host={os.environ['PGHOST']} "
        f"port={os.environ.get('PGPORT', '5432')} "
        f"dbname={os.environ['PGDATABASE']} "
        f"user={os.environ['PGUSER']} "
        f"password={os.environ['PGPASSWORD']}"
    )

    # Load config
    with open(config_path) as f:
        config = yaml.safe_load(f)

    if mode == "complete":
        # Complete export with partitioning
        for coll in config.get("collections", []):
            collection = coll["name"]
            partition_by = coll.get("partition_by")

            if partition_by == "year":
                start_year = coll.get("start_year", 2015)
                end_year = datetime.now(timezone.utc).year

                for year in range(start_year, end_year + 1):
                    start = datetime(year, 1, 1, tzinfo=timezone.utc)
                    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
                    output = f"{output_base}/{collection}/items_{year}.parquet"

                    print(f"Exporting {collection} for {year}")
                    pgstac_to_parquet(
                        conninfo=conninfo,
                        output_path=output,
                        collection=collection,
                        start_datetime=start,
                        end_datetime=end,
                    )
            else:
                # Single file
                output = f"{output_base}/{collection}/items.parquet"
                print(f"Exporting {collection}")
                pgstac_to_parquet(
                    conninfo=conninfo,
                    output_path=output,
                    collection=collection,
                )
    else:
        # Incremental sync
        state_file = Path(output_base) / ".last_sync"
        updated_after = None

        if state_file.exists():
            updated_after = datetime.fromisoformat(state_file.read_text().strip())
            print(f"Syncing since {updated_after}")

        sync_pgstac_to_parquet(
            conninfo=conninfo,
            output_path=output_base,
            updated_after=updated_after,
        )

        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(datetime.now(timezone.utc).isoformat())

    print("Export complete")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
