import logging

from django.conf import settings
from time import perf_counter
from typing import Callable, Dict, List, Optional

from usaspending_api.etl.elasticsearch_loader_helpers.utilities import (
    convert_postgres_json_array_to_list,
    format_log,
    TaskSpec,
)


logger = logging.getLogger("script")


def transform_award_data(worker: TaskSpec, records: List[dict]) -> List[dict]:
    converters = {}
    return transform_data(worker, records, converters, settings.ES_ROUTING_FIELD)


def transform_transaction_data(worker: TaskSpec, records: List[dict]) -> List[dict]:
    converters = {
        "federal_accounts": convert_postgres_json_array_to_list,
    }
    return transform_data(worker, records, converters, settings.ES_ROUTING_FIELD)


def transform_covid19_faba_data(worker: TaskSpec, records: List[dict]) -> List[dict]:
    logger.info(format_log(f"Transforming data", name=worker.name, action="Transform"))
    start = perf_counter()
    results = {}

    for record in records:
        es_id_field = record[worker.field_for_es_id]
        disinct_award_key = record.pop("financial_account_distinct_award_key")
        award_id = record.pop("award_id")
        award_type = record.pop("type")
        generated_unique_award_id = record.pop("generated_unique_award_id")
        total_loan_value = record.pop("total_loan_value")
        obligated_sum = record.get("transaction_obligated_amount") or 0
        outlay_sum = record.get("gross_outlay_amount_by_award_cpe") or 0
        temp_key = disinct_award_key
        if temp_key not in results:
            results[temp_key] = {
                "financial_account_distinct_award_key": disinct_award_key,
                "award_id": award_id,
                "type": award_type,
                "generated_unique_award_id": generated_unique_award_id,
                "total_loan_value": total_loan_value,
                "financial_accounts_by_award": list(),
                "total_covid_obligation": 0,
                "total_covid_outlay": 0,
                "_id": es_id_field,
            }
        results[temp_key]["total_covid_outlay"] += outlay_sum
        results[temp_key]["total_covid_obligation"] += obligated_sum
        results[temp_key]["financial_accounts_by_award"].append(record)

    if len(results) != len(records):
        msg = f"Transformed {len(records)} database records into {len(results)} documents for ingest"
        logger.info(format_log(msg, name=worker.name, action="Transform"))

    msg = f"Transformation operation took {perf_counter() - start:.2f}s"
    logger.info(format_log(msg, name=worker.name, action="Transform"))
    return list(results.values())  # don't need the dict key, return a list of the dict values


def transform_data(
    worker: TaskSpec, records: List[dict], converters: Dict[str, Callable], routing_field: Optional[str] = None
) -> List[dict]:
    logger.info(format_log(f"Transforming data", name=worker.name, action="Transform"))
    start = perf_counter()

    for record in records:
        for field, converter in converters.items():
            record[field] = converter(record[field])

        # Route all documents with the same recipient to the same shard
        # This allows for accuracy and early-termination of "top N" recipient category aggregation queries
        # Recipient is are highest-cardinality category with over 2M unique values to aggregate against,
        # and this is needed for performance
        # ES helper will pop any "meta" fields like "routing" from provided data dict and use them in the action
        if routing_field:
            record["routing"] = record[routing_field]

        # Explicitly setting the ES _id field to match the postgres PK value allows
        # bulk index operations to be upserts without creating duplicate documents
        # IF and ONLY IF a routing meta field is not also provided (one whose value differs
        # from the doc _id field). If explicit routing is done, UPSERTs may cause duplicates,
        # so docs must be deleted before UPSERTed. (More info in streaming_post_to_es(...))
        record["_id"] = record[worker.field_for_es_id]

    duration = perf_counter() - start
    logger.info(format_log(f"Transformation operation took {duration:.2f}s", name=worker.name, action="Transform"))
    return records
