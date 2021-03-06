#!/usr/bin/env python3

import argparse
import glob
import hashlib
import os
import copy

from shared_sql_generator import (
    COMPONENT_DIR,
    generate_uid,
    HERE,
    ingest_json,
    make_indexes_sql,
    make_modification_sql,
    make_table_drops,
    make_table_inserts,
    make_matview_empty,
    make_matview_refresh,
    TEMPLATE,
)

# Usage: python chunked_matview_sql_generator.py --file <file_name> (from usaspending_api/database_scripts/matview_generator)
#        ^--- Will clobber files in usaspending_api/database_scripts/matviews

"""
POSTGRES INDEX FORMAT
    CREATE [ UNIQUE ] INDEX [ name ] ON table_name [ USING method ]
    ( { column_name | ( expression ) } [ COLLATE collation ]
        [ opclass ] [ ASC | DESC ] [ NULLS { FIRST | LAST } ] [, ...] )
    [ WITH ( storage_parameter = value [, ... ] ) ]
    [ WHERE predicate ]

EXAMPLE SQL DESCRIPTION JSON FILE:

{   "final_name": "example_matview",
    "matview_sql": [
    "SELECT",
    "  action_date,",
    "  fiscal_year,",
    "  awards.type,",
    "  awards.category,",
    "FROM",
    "  awards",
    "LEFT OUTER JOIN",
    "  transaction_normalized ON (awards.latest_transaction_id = id)",
    "WHERE",
    "  action_date >= '2000-10-01'",
    "ORDER BY",
    "  action_date DESC"

    ],
    "index": {
        "name": "<name>",
        "columns": [
            {
                "name": "<col name>",
                "order": "DESC|ASC NULLS FIRST|LAST",
                "collation": "<collation>",
                "opclass": "<opclass"
            }
        ],
        "where": "<where clause>",
        "unique": true,
        "method": "<method>"
    }
}
"""

GLOBAL_ARGS = None
UNIQUE_STRING = None


def make_matview_drops(final_matview_name):
    return [TEMPLATE["drop_matview"].format(final_matview_name)]


def make_matview_create(final_matview_name, sql):
    matview_sql = "\n".join(sql)
    return [TEMPLATE["create_matview"].format(final_matview_name, matview_sql, "")]


def make_table_create(table_name):
    table_temp_name = table_name + "_temp"
    # Use the first Matview as the table definition
    matview_name = table_name + "_0"
    return [
        TEMPLATE["drop_table"].format(table_temp_name),
        TEMPLATE["create_table"].format(table_temp_name, matview_name),
    ]


def make_index_rename_sql(old_indexes, new_indexes):
    sql_strings = []
    sql_strings += old_indexes
    sql_strings.append("")
    sql_strings += new_indexes
    return sql_strings


def make_rename_sql(table_name, old_indexes, new_indexes):
    table_temp_name = table_name + "_temp"
    table_archive_name = table_name + "_old"
    sql_strings = []
    sql_strings.append(TEMPLATE["drop_table"].format(table_archive_name))
    sql_strings.append(TEMPLATE["rename_table"].format("IF EXISTS ", table_name, table_archive_name))
    sql_strings += old_indexes
    sql_strings.append("")
    sql_strings.append(TEMPLATE["rename_table"].format("", table_temp_name, table_name))
    sql_strings += new_indexes
    sql_strings.append("")
    return sql_strings


def create_all_sql_strings(sql_json):
    """ Desired ordering of steps for final SQL:
        1. Drop existing "_temp" and "_old" matviews
        2. Create new matview
        3. analyze verbose <matview>
    """
    final_sql_strings = []

    matview_name = sql_json["final_name"]

    final_sql_strings.extend(make_matview_drops(matview_name))
    final_sql_strings.append("")
    final_sql_strings.extend(make_matview_create(matview_name, sql_json["matview_sql"]))

    final_sql_strings.append("")
    final_sql_strings.extend(make_modification_sql(matview_name, GLOBAL_ARGS.quiet))
    return final_sql_strings


def write_sql_file(str_list, filename):
    fname = filename + ".sql"

    print_debug("Creating file: {}".format(fname))
    with open(fname, "w") as f:
        fstring = "\n".join(str_list)
        f.write(fstring)
        f.write("\n")


def create_componentized_files(sql_json):
    table_name = sql_json["final_name"]
    table_temp_name = table_name + "_temp"
    filename_base = os.path.join(DEST_FOLDER, COMPONENT_DIR, sql_json["final_name"])

    create_table = make_table_create(table_name)
    write_sql_file(create_table, filename_base + "__create")

    insert_into_table = make_table_inserts(table_name, GLOBAL_ARGS.chunk_count)
    write_sql_file(insert_into_table, filename_base + "__inserts")

    create_indexes, rename_old_indexes, rename_new_indexes = make_indexes_sql(
        sql_json, table_temp_name, UNIQUE_STRING, False, GLOBAL_ARGS.quiet
    )
    write_sql_file(create_indexes, filename_base + "__indexes")

    sql_strings = make_rename_sql(table_name, rename_old_indexes, rename_new_indexes)
    write_sql_file(sql_strings, filename_base + "__renames")

    sql_strings = make_modification_sql(table_name, GLOBAL_ARGS.quiet)
    write_sql_file(sql_strings, filename_base + "__mods")

    sql_strings = make_table_drops(table_name)
    write_sql_file(sql_strings, filename_base + "__drops")

    sql_strings = make_matview_empty(table_name, GLOBAL_ARGS.chunk_count)
    write_sql_file(sql_strings, filename_base + "__empty")


def create_chunked_componentized_files(sql_json):
    table_name = sql_json["final_name"]
    filename_base = os.path.join(DEST_FOLDER, COMPONENT_DIR, sql_json["final_name"])

    sql_strings = make_matview_drops(table_name)
    write_sql_file(sql_strings, filename_base + "__drops")

    sql_strings = make_matview_refresh(table_name, "")
    write_sql_file(sql_strings, filename_base + "__refresh")

    sql_strings = make_matview_create(table_name, sql_json["matview_sql"])
    write_sql_file(sql_strings, filename_base + "__matview")


def create_monolith_file(sql_json):
    sql_strings = create_all_sql_strings(sql_json)
    print_debug('Preparing to store "{}" in sql file'.format(sql_json["final_name"]))
    write_sql_file(sql_strings, os.path.join(DEST_FOLDER, sql_json["final_name"]))


def add_chunk_strings(sql_json, chunk):
    chunked_sql_json = copy.deepcopy(sql_json)

    chunk_count = GLOBAL_ARGS.chunk_count

    if chunk_count > 1:
        chunked_sql_json["final_name"] = f"{chunked_sql_json['final_name']}_{chunk}"
        chunked_sql_json["matview_sql"].append("  AND transaction_normalized.id % {} = {}".format(chunk_count, chunk))

    return chunked_sql_json


def print_debug(msg):
    if not GLOBAL_ARGS.quiet:
        print(msg)


def main(source_file):
    global UNIQUE_STRING
    commit_hash = generate_uid(9, source_file)
    random_chars = hashlib.md5(source_file.encode("utf-8")).hexdigest()[:3]
    UNIQUE_STRING = commit_hash + random_chars

    try:
        sql_json = ingest_json(source_file)
    except Exception as e:
        print("Error on Matview source JSON file: {}".format(source_file))
        print(e)
        raise SystemExit(1)

    create_componentized_files(sql_json)
    for chunk in range(0, GLOBAL_ARGS.chunk_count):
        chunked_sql_json = add_chunk_strings(sql_json, chunk)

        create_monolith_file(chunked_sql_json)
        create_chunked_componentized_files(chunked_sql_json)

    print_debug("Done")


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        prog="matview_sql_generator.py", description="Generates all of the necessary SQL files for jenkins scripts"
    )
    arg_parser.add_argument(
        "--dest", type=str, default="../chunked_matviews/", help="Destination folder for all generated sql files"
    )
    arg_parser.add_argument(
        "--file", type=str, default=None, help="filepath to the json file containing the sql description"
    )
    arg_parser.add_argument(
        "-q", "--quiet", action="store_true", help="Flag to suppress stdout when there are no errors"
    )
    arg_parser.add_argument(
        "-c", "--chunk-count", type=int, default=1, help="When value >=2, split matview into multiple SQL files"
    )
    GLOBAL_ARGS = arg_parser.parse_args()

    DEST_FOLDER = GLOBAL_ARGS.dest
    if not os.path.exists(os.path.join(DEST_FOLDER, COMPONENT_DIR)):
        os.makedirs(os.path.join(DEST_FOLDER, COMPONENT_DIR))

    if GLOBAL_ARGS.file is not None:
        if os.path.isfile(GLOBAL_ARGS.file):
            print_debug("Creating matview SQL using {}".format(GLOBAL_ARGS.file))
            main(GLOBAL_ARGS.file)
    else:
        all_files = glob.glob(os.path.join(HERE, "*.json"))
        for f in all_files:
            print_debug("\n==== {}".format(f))
            main(f)
