FORMAT: 1A
HOST: https://api.usaspending.gov

# Agencies Reporting Publish Dates History [/api/v2/reporting/submission_history/{agency_code}/{fiscal_year}/{fiscal_period}]

This endpoint is used to power USAspending.gov's About the Data \| Agencies submission history modal.

## GET

This endpoint returns the history of publication and certification dates for a single agency's submission.

+ Parameters
    + `agency_code`: `020` (required, string)
        The specific agency code.
    + `fiscal_year`: 2020 (required, number)
        The fiscal year of the submission
    + `fiscal_period`: 10 (required, number)
        The fiscal period of the submission. valid values: 2-12 (2 = November ... 12 = September)
        For retriving quarterly submissions, provide the period which equals 'quarter * 3' (e.g. Q2 = P6)

+ Response 200 (application/json)

    + Attributes (object)
        + `results` (required, array[SubmissionHistory], fixed-type)
    + Body

            {
                "results": [
                    {
                        "publication_date": "2020-10-11T11:59:21Z",
                        "certification_date": "2020-10-22T11:59:21Z"
                    },
                    {
                        "publication_date": "2020-07-10T11:59:21Z",
                        "certification_date": "2020-07-11T11:59:21Z"
                    },
                    {
                        "publication_date": "2020-07-10T11:59:21Z",
                        "certification_date": null
                    }
                ]
            }

# Data Structures

## SubmissionHistory (object)
+ `publication_date` (required, string, nullable)
+ `certification_date` (required, string, nullable)
