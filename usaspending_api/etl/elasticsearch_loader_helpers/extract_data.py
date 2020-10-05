import logging

from time import perf_counter
from usaspending_api.etl.elasticsearch_loader_helpers.utilities import format_log, execute_sql_statement

logger = logging.getLogger("script")

COUNT_SQL = """
SELECT COUNT(*) AS count
FROM "{view}"
WHERE "update_date" >= '{update_date}'
"""

EXTRACT_SQL = """
    SELECT *
    FROM "{view}"
    WHERE "update_date" >= '{update_date}' AND "{id_col}" IN
    (SELECT id from transaction_normalized WHERE mod("id", {divisor}) = {remainder})
"""


def count_of_records_to_process(config):
    start = perf_counter()
    count_sql = COUNT_SQL.format(update_date=config["starting_date"], view=config["sql_view"])
    count = execute_sql_statement(count_sql, True, config["verbose"])[0]["count"]
    msg = f"Found {count:,} {config['data_type']} DB records, took {perf_counter() - start:.2f}s"
    logger.info(format_log(msg, process="Extract"))
    return count


def extract_records(worker):
    start = perf_counter()
    logger.info(format_log(f"Extracting data from source", job=worker.name, process="Extract"))

    try:
        records = execute_sql_statement(worker.sql, True)
    except Exception as e:
        logger.exception(f"Worker {worker.name} failed with '{worker.sql}'")
        raise e

    msg = f"{len(records):,} records extracted in {perf_counter() - start:.2f}s"
    logger.info(format_log(msg, job=worker.name, process="Extract"))
    return records
