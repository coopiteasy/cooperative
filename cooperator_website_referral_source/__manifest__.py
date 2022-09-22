# SPDX-FileCopyrightText: 2022 Coop IT Easy SC
#
# SPDX-License-Identifier: AGPL-3.0-or-later

{
    "name": "Cooperator Website Refferral",
    "summary": """
        Add a Selection field in the form to select
        how the respondent discovered the cooperative.
        """,
    "version": "12.0.1.0.0",
    "category": "Cooperative management",
    "website": "https://coopiteasy.be",
    "author": "Coop IT Easy SC",
    "license": "AGPL-3",
    "application": False,
    "depends": ["cooperator_website"],
    "excludes": [],
    "data": [
        "views/referral_source_view.xml",
        "views/res_company_views.xml",
        "views/subscription_template.xml",
    ],
    "demo": [],
    "qweb": [],
}
