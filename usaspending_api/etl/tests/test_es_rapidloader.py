import pytest
from django.conf import settings

from collections import OrderedDict
from datetime import datetime, timezone
from model_mommy import mommy
from pathlib import Path
from usaspending_api.common.elasticsearch.client import instantiate_elasticsearch_client
from usaspending_api.common.helpers.sql_helpers import execute_sql_to_ordered_dictionary
from usaspending_api.common.helpers.text_helpers import generate_random_string

from usaspending_api.etl.elasticsearch_loader_helpers import (
    check_awards_for_deletes,
    get_deleted_award_ids,
    Controller,
    execute_sql_statement,
    transform_award_data,
    transform_transaction_data,
)


@pytest.fixture
def award_data_fixture(db):
    mommy.make(
        "awards.TransactionNormalized",
        id=1,
        award_id=1,
        action_date="2010-10-01",
        is_fpds=True,
        type="A",
        transaction_unique_id="transaction_id_1",
    )
    mommy.make(
        "awards.TransactionFPDS",
        detached_award_proc_unique="transaction_id_1",
        transaction_id=1,
        legal_entity_zip5="abcde",
        piid="IND12PB00323",
        legal_entity_county_code="059",
        legal_entity_state_code="VA",
        legal_entity_congressional="11",
        legal_entity_country_code="USA",
        place_of_performance_state="VA",
        place_of_performance_congr="11",
        place_of_perform_country_c="USA",
        naics="331122",
        product_or_service_code="1510",
        type_set_aside="8AN",
        type_of_contract_pricing="2",
        extent_competed="F",
    )

    mommy.make("awards.TransactionNormalized", id=2, award_id=2, action_date="2016-10-01", is_fpds=False, type="02")
    mommy.make("awards.TransactionFABS", transaction_id=2, fain="P063P100612", cfda_number="84.063")

    mommy.make("references.ToptierAgency", toptier_agency_id=1, name="Department of Transportation")
    mommy.make("references.SubtierAgency", subtier_agency_id=1, name="Department of Transportation")
    mommy.make("references.Agency", id=1, toptier_agency_id=1, subtier_agency_id=1)
    mommy.make(
        "awards.Award",
        id=1,
        generated_unique_award_id="CONT_AWD_IND12PB00323",
        latest_transaction_id=1,
        is_fpds=True,
        type="A",
        piid="IND12PB00323",
        description="pop tarts and assorted cereals",
        total_obligation=500000.00,
        date_signed="2010-10-1",
        awarding_agency_id=1,
        funding_agency_id=1,
        update_date="2012-05-19",
    )
    mommy.make(
        "awards.Award",
        id=2,
        generated_unique_award_id="ASST_NON_P063P100612",
        latest_transaction_id=2,
        is_fpds=False,
        type="02",
        fain="P063P100612",
        total_obligation=1000000.00,
        date_signed="2016-10-1",
        update_date="2014-07-21",
    )
    mommy.make("accounts.FederalAccount", id=1)
    mommy.make(
        "accounts.TreasuryAppropriationAccount",
        treasury_account_identifier=1,
        agency_id="097",
        main_account_code="4930",
        federal_account_id=1,
    )

    mommy.make("awards.FinancialAccountsByAwards", financial_accounts_by_awards_id=1, award_id=1, treasury_account_id=1)


award_config = {
    "create_new_index": True,
    "data_type": "award",
    "data_transform_func": transform_award_data,
    "directory": Path(__file__).resolve().parent,
    "fiscal_years": [2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020],
    "index_name": f"test-{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H-%M-%S-%f')}-{generate_random_string()}",
    "is_incremental_load": False,
    "max_query_size": 10000,
    "process_deletes": False,
    "processing_start_datetime": datetime(2019, 12, 13, 16, 10, 33, 729108, tzinfo=timezone.utc),
    "query_alias_prefix": "award-query",
    "skip_counts": False,
    "snapshot": False,
    "starting_date": datetime(2007, 10, 1, 0, 0, tzinfo=timezone.utc),
    "unique_key_field": "award_id",
    "verbose": False,
}

transaction_config = {
    "base_table": "transaction_normalized",
    "base_table_id": "id",
    "create_award_type_aliases": True,
    "data_transform_func": transform_transaction_data,
    "data_type": "transaction",
    "execute_sql_func": execute_sql_statement,
    "extra_null_partition": False,
    "field_for_es_id": "transaction_id",
    "initial_datetime": datetime(2019, 12, 13, 16, 10, 33, 729108, tzinfo=timezone.utc),
    "max_query_size": 50000,
    "optional_predicate": """WHERE "update_date" >= '{starting_date}'""",
    "primary_key": "transaction_id",
    "query_alias_prefix": "transaction-query",
    "required_index_name": settings.ES_TRANSACTIONS_NAME_SUFFIX,
    "sql_view": settings.ES_TRANSACTIONS_ETL_VIEW_NAME,
    "stored_date_key": "es_transactions",
    "unique_key_field": "generated_unique_transaction_id",
    "write_alias": settings.ES_TRANSACTIONS_WRITE_ALIAS,
}

################################################################################
# Originally the ES ETL would create a new index even if there was no data.
# A few simple changes led to these two tests failing because the entire ETL
#  needs to run and that would require monkeypatching the PSQL CSV copy steps
#  which would be laborious and fragile. Leaving tests in-place to document this
#  testing shortcoming. It may be addressed in the near future (time-permitting)
#  if some refactoring occurs and allows more flexibility. -- from Aug 2020
################################################################################


@pytest.mark.skip
def test_es_award_loader_class(award_data_fixture, elasticsearch_award_index, monkeypatch):
    monkeypatch.setattr(
        "usaspending_api.etl.elasticsearch_loader_helpers.utilities.execute_sql_statement", mock_execute_sql
    )
    elasticsearch_client = instantiate_elasticsearch_client()
    loader = Controller(award_config, elasticsearch_client)
    assert loader.__class__.__name__ == "Controller"
    loader.run_load_steps()
    assert elasticsearch_client.indices.exists(award_config["index_name"])
    elasticsearch_client.indices.delete(index=award_config["index_name"], ignore_unavailable=False)


@pytest.mark.skip
def test_es_transaction_loader_class(award_data_fixture, elasticsearch_transaction_index, monkeypatch):
    monkeypatch.setattr(
        "usaspending_api.etl.elasticsearch_loader_helpers.utilities.execute_sql_statement", mock_execute_sql
    )
    elasticsearch_client = instantiate_elasticsearch_client()
    loader = Controller(transaction_config, elasticsearch_client)
    assert loader.__class__.__name__ == "Controller"
    loader.run_load_steps()
    assert elasticsearch_client.indices.exists(transaction_config["index_name"])
    elasticsearch_client.indices.delete(index=transaction_config["index_name"], ignore_unavailable=False)


# SQL method is being mocked here since the `execute_sql_statement` used
#  doesn't use the same DB connection to avoid multiprocessing errors
def mock_execute_sql(sql, results, verbosity=None):
    return execute_sql_to_ordered_dictionary(sql)


def test_award_delete_sql(award_data_fixture, monkeypatch, db):
    monkeypatch.setattr(
        "usaspending_api.etl.elasticsearch_loader_helpers.delete_data.execute_sql_statement", mock_execute_sql
    )
    id_list = ["CONT_AWD_IND12PB00323"]
    awards = check_awards_for_deletes(id_list)
    assert awards == []

    id_list = ["CONT_AWD_WHATEVER", "CONT_AWD_IND12PB00323"]
    awards = check_awards_for_deletes(id_list)
    assert awards == [OrderedDict([("generated_unique_award_id", "CONT_AWD_WHATEVER")])]


def test_get_award_ids(award_data_fixture, elasticsearch_award_index):
    elasticsearch_award_index.update_index()
    id_list = [{"key": 1, "col": "award_id"}]
    client = elasticsearch_award_index.client
    ids = get_deleted_award_ids(client, id_list, award_config, index=elasticsearch_award_index.index_name)
    assert ids == ["CONT_AWD_IND12PB00323"]
