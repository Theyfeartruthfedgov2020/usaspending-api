FORMAT: 1A
HOST: https://api.usaspending.gov

# Disaster Spending By Geography [/api/v2/disaster/spending_by_geography/]

This endpoint provides geographical spending information from emergency/disaster funding based on recipient location.

## POST

+ Request (application/json)
    + Schema

            {
                "$schema": "http://json-schema.org/draft-04/schema#",
                "type": "string"
            }
    + Attributes (object)
        + `filter` (required, Filter, fixed-type)
        + `geo_layer` (required, enum[string])
            Set the type of shape codes in the response
            + Members
                + `state`
                + `county`
                + `district`
        + `geo_layer_filters` (required, array[string])
            Allows us to only request data for what is currently in view in the map
        + `spending_type` (required, enum[string])
            + Members
                + `obligation`
                + `outlay`
                + `face_value_of_loan`

    + Body

            {
                "filter": {
                    "def_codes": ["L", "M", "N", "O", "P"]
                },
                "geo_layer": "state",
                "geo_layer_filters": ["NE", "WY", "CO", "IA", "IL", "MI", "IN", "TX"],
                "spending_type": "obligation"
            }

+ Response 200 (application/json)
    + Attributes (object)
        + `geo_layer` (required, enum[string], fixed-type)
            + Members
                + `state`
                + `county`
                + `district`
        + `spending_type` (required, enum[string])
            + Members
                + `obligation`
                + `outlay`
                + `face_value_of_loan`
        + `results` (array[GeographyTypeResult], fixed-type)
        + `messages` (optional, array[string], fixed-type)
            An array of warnings or instructional directives to aid consumers of this endpoint with development and debugging.
    + Body

            {
                "geo_layer": "state",
                "spending_type": "obligation",
                "results": [
                    {
                        "shape_code": "ND",
                        "amount": 4771026.93,
                        "display_name": "North Dakota",
                        "population": 762062,
                        "per_capita": 6.26
                    },
                    {
                        "shape_code": "NV",
                        "amount": 26928552.59,
                        "display_name": "Nevada",
                        "population": 3080156,
                        "per_capita": 8.74
                    },
                    {
                        "shape_code": "OH",
                        "amount": 187505278.16,
                        "display_name": "Ohio",
                        "population": 11689100,
                        "per_capita": 16.04
                    }
                ]
            }

# Data Structures

## Filter (object)
+ `def_codes` (required, array[DEFC], fixed-type)
    Return an award if an of the DEF Codes match the supplied filter since an Award can have multiple DEF Codes.
+ `award_type_codes` (optional, array[AwardTypeCodes], fixed-type)

## GeographyTypeResult (object)
+ `amount` (required, number)
    Dollar obligated or outlayed amount (depending on the `spending_type` requested)
+ `display_name` (required, string)
+ `shape_code` (required, string)
+ `population` (required, number, nullable)
+ `per_capita` (required, number, nullable)


## DEFC (enum[string])
List of Disaster Emergency Fund (DEF) Codes (DEFC) defined by legislation at the time of writing

### Members
+ `A`
+ `B`
+ `C`
+ `D`
+ `E`
+ `F`
+ `G`
+ `H`
+ `I`
+ `J`
+ `K`
+ `L`
+ `M`
+ `N`
+ `O`
+ `P`
+ `Q`
+ `R`
+ `S`
+ `T`
+ `9`

## AwardTypeCodes (enum[string])
List of procurement and assistance award type codes supported by USAspending.gov

### Members
+ `02`
+ `03`
+ `04`
+ `05`
+ `06`
+ `07`
+ `08`
+ `09`
+ `10`
+ `11`
+ `A`
+ `B`
+ `C`
+ `D`
+ `IDV_A`
+ `IDV_B_A`
+ `IDV_B_B`
+ `IDV_B_C`
+ `IDV_B`
+ `IDV_C`
+ `IDV_D`
+ `IDV_E`
