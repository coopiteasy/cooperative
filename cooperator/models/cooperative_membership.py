# SPDX-FileCopyrightText: 2019 Coop IT Easy SC
# SPDX-FileContributor: Houssine Bakkali <houssine@coopiteasy.be>
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from odoo import api, fields, models

from . import share_type


class CooperativeMembership(models.Model):
    _name = "cooperative.membership"
    _description = "Cooperative Membership"
    _check_company_auto = True
    _sql_constraints = [
        (
            "company_id_partner_id_key",
            "unique (company_id, partner_id)",
            "Only one cooperative membership record can exist per partner (per company)",
        ),
        (
            # "numbe" instead of "number" because the constraint name is
            # appended to the table name and it must be 63 characters maximum.
            # following the default postgresql naming by appending the column
            # names and truncating before _key.
            "company_id_cooperator_register_numbe_key",
            "unique (company_id, cooperator_register_number)",
            "A cooperator register number must be unique (per company)",
        ),
    ]
    _order = "cooperator_register_number"

    @api.depends("partner_id.share_ids")
    def _compute_effective_date(self):
        # TODO change it to compute it from the share register
        for record in self:
            if record.share_ids:
                record.effective_date = record.share_ids[0].effective_date
            else:
                record.effective_date = False

    def _get_share_type(self):
        return share_type.get_share_types(self.env)

    @api.depends(
        "partner_id.share_ids",
        "partner_id.share_ids.share_product_id.default_code",
        "partner_id.share_ids.share_number",
    )
    def _compute_cooperator_type(self):
        for record in self:
            share_type = ""
            for line in record.share_ids:
                if line.share_number > 0:
                    share_type = line.share_product_id.default_code
                    break
            record.cooperator_type = share_type

    @api.depends(
        "partner_id.share_ids.share_number", "partner_id.share_ids.share_unit_price"
    )
    def _compute_share_info(self):
        for record in self:
            number_of_share = 0
            total_value = 0.0
            for line in record.share_ids:
                number_of_share += line.share_number
                total_value += line.share_unit_price * line.share_number
            record.number_of_share = number_of_share
            record.total_value = total_value

    @api.depends("member", "partner_id.subscription_request_ids.state")
    def _compute_coop_candidate(self):
        for record in self:
            if record.member:
                is_candidate = False
            else:
                sub_requests = record.subscription_request_ids.filtered(
                    lambda record: record.state == "done"
                )
                is_candidate = bool(sub_requests)

            record.coop_candidate = is_candidate

    @api.depends("partner_id.share_ids", "company_id")
    def _compute_share_ids(self):
        share_line_model = self.env["share.line"]
        for record in self:
            record.share_ids = share_line_model.search(
                [
                    ("partner_id", "=", record.partner_id.id),
                    ("company_id", "=", record.company_id.id),
                ]
            )

    def _search_share_ids(self, operator, value):
        return [
            ("partner_id.share_ids.company_id", "=", self.company_id.id),
            ("partner_id.share_ids", operator, value),
        ]

    @api.depends("partner_id.subscription_request_ids", "company_id")
    def _compute_subscription_request_ids(self):
        subscription_request_model = self.env["subscription.request"]
        for record in self:
            record.subscription_request_ids = subscription_request_model.search(
                [
                    ("partner_id", "=", record.partner_id.id),
                    ("company_id", "=", record.company_id.id),
                ]
            )

    def _search_subscription_request_ids(self, operator, value):
        return [
            ("partner_id.subscription_request_ids.company_id", "=", self.company_id.id),
            ("partner_id.subscription_request_ids", operator, value),
        ]

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    partner_id = fields.Many2one(
        "res.partner",
        "Partner",
        required=True,
        readonly=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char(related="partner_id.name")
    is_company = fields.Boolean(related="partner_id.is_company", store=True)
    email = fields.Char(related="partner_id.email")
    # todo: remove this. this was used on res.partner. the existence of a
    # cooperative.membership record should be enough.
    cooperator = fields.Boolean(
        help="Check this box if this contact is a cooperator (effective or not).",
        readonly=True,
        copy=False,
    )
    member = fields.Boolean(
        string="Effective cooperator",
        help="Check this box if this cooperator is an effective member.",
        readonly=True,
        copy=False,
    )
    coop_candidate = fields.Boolean(
        string="Cooperator candidate",
        compute=_compute_coop_candidate,
        store=True,
    )
    old_member = fields.Boolean(
        string="Old cooperator",
        help="Check this box if this cooperator is no more an effective member.",
        readonly=True,
    )
    share_ids = fields.One2many(
        "share.line",
        string="Share Lines",
        compute=_compute_share_ids,
        search=_search_share_ids,
    )
    cooperator_register_number = fields.Integer(
        string="Cooperator Number",
        readonly=True,
        copy=False,
        group_operator=None,
    )
    number_of_share = fields.Integer(
        compute=_compute_share_info,
        string="Number of share",
        store=True,
    )
    total_value = fields.Float(
        compute=_compute_share_info,
        string="Total value of shares",
        store=True,
    )
    cooperator_type = fields.Selection(
        selection=_get_share_type,
        compute=_compute_cooperator_type,
        store=True,
    )
    effective_date = fields.Date(compute=_compute_effective_date, store=True)
    subscription_request_ids = fields.One2many(
        "subscription.request",
        string="Subscription request",
        compute=_compute_subscription_request_ids,
        search=_search_subscription_request_ids,
    )
    data_policy_approved = fields.Boolean(string="Approved Data Policy")
    internal_rules_approved = fields.Boolean(string="Approved Internal Rules")
    financial_risk_approved = fields.Boolean(string="Approved Financial Risk")
    generic_rules_approved = fields.Boolean(string="Approved generic rules")

    def get_cooperator_from_email(self, email):
        if email:
            email = email.strip()
        # email could be falsy or be only made of whitespace.
        if not email:
            return self.browse()
        cooperator = self.search(
            [("cooperator", "=", True), ("email", "=", email)], limit=1
        )
        if not cooperator:
            partner = self.env["res.partner"].search([("email", "=", email)], limit=1)
            if partner:
                cooperator = partner.cooperator_id
        return cooperator

    def get_cooperator_from_crn(self, company_register_number):
        if company_register_number:
            company_register_number = company_register_number.strip()
        # company_register_number could be falsy or be only made of whitespace.
        if not company_register_number:
            return self.browse()
        cooperator = self.search(
            [
                ("cooperator", "=", True),
                ("company_register_number", "=", company_register_number),
            ],
            limit=1,
        )
        if not cooperator:
            partner = self.env["res.partner"].search(
                [("company_register_number", "=", company_register_number)], limit=1
            )
            if partner:
                cooperator = partner.cooperator_id
        return cooperator
