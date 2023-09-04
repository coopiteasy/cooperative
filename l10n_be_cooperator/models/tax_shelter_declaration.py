# SPDX-FileCopyrightText: 2017 Open Architects Consulting SPRL
# SPDX-FileCopyrightText: 2018 Coop IT Easy SC
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from odoo import fields, models

TYPE_MAP = {
    "subscription": "subscribed",
    "transfer": "transfered",
    "sell_back": "resold",
}


class TaxShelterDeclaration(models.Model):
    _name = "tax.shelter.declaration"
    _description = "Tax Shelter Declaration"

    name = fields.Char(string="Declaration year", required=True)
    fiscal_year = fields.Char(string="Fiscal year", required=True)
    tax_shelter_certificates = fields.One2many(
        "tax.shelter.certificate",
        "declaration_id",
        string="Tax shelter certificates",
        readonly=True,
    )
    date_from = fields.Date(string="Date from", required=True)
    date_to = fields.Date(string="Date to", required=True)
    month_from = fields.Char(string="Month from", required=True)
    month_to = fields.Char(string="Month to", required=True)
    tax_shelter_percentage = fields.Selection(
        [("30", "30%"), ("45", "45%")],
        string="Tax Shelter percentage",
        required=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("computed", "Computed"),
            ("validated", "Validated"),
        ],
        required=True,
        default="draft",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        change_default=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    tax_shelter_capital_limit = fields.Float(
        string="Tax shelter capital limit", required=True
    )
    previously_subscribed_capital = fields.Float(
        string="Capital previously subscribed", readonly=True
    )
    excluded_cooperator = fields.Many2many(
        "res.partner",
        string="Excluded cooperator",
        domain=[("cooperator", "=", True)],
        help="If these cooperator have"
        " subscribed share during the time"
        " frame of this Tax Shelter "
        "Declaration. They will be marked "
        "as non eligible",
    )

    def _excluded_from_declaration(self, entry):
        if entry.date >= self.date_from and entry.date <= self.date_to:
            declaration = self
        else:
            declaration = self.search(
                [
                    ("date_from", "<=", entry.date),
                    ("date_to", ">=", entry.date),
                ]
            )
        if entry.partner_id.id in declaration.excluded_cooperator.ids:
            return True
        return False

    def _prepare_line(self, certificate, entry, ongoing_capital_sub, excluded):
        line_vals = {}
        line_vals["tax_shelter_certificate"] = certificate.id
        line_vals["share_type"] = entry.share_product_id.id
        line_vals["share_short_name"] = entry.share_short_name
        line_vals["share_unit_price"] = entry.share_unit_price
        line_vals["quantity"] = entry.quantity
        line_vals["transaction_date"] = entry.date
        line_vals["type"] = TYPE_MAP[entry.type]
        if entry.type == "subscription":
            if not excluded:
                capital_after_sub = ongoing_capital_sub + entry.total_amount_line
            else:
                capital_after_sub = ongoing_capital_sub
            line_vals["capital_before_sub"] = ongoing_capital_sub
            line_vals["capital_after_sub"] = capital_after_sub
            line_vals["capital_limit"] = self.tax_shelter_capital_limit
            if ongoing_capital_sub < self.tax_shelter_capital_limit and not excluded:
                line_vals["tax_shelter"] = True
        return line_vals

    def _compute_certificates(self, entries, partner_certificate):
        ongoing_capital_sub = 0.0
        for entry in entries:
            certificate = partner_certificate.get(entry.partner_id.id, False)

            if not certificate:
                # create a certificate for this cooperator
                cert_vals = {}
                cert_vals["declaration_id"] = self.id
                cert_vals["partner_id"] = entry.partner_id.id
                cert_vals[
                    "cooperator_number"
                ] = entry.partner_id.cooperator_register_number
                certificate = self.env["tax.shelter.certificate"].create(cert_vals)
                partner_certificate[entry.partner_id.id] = certificate
            excluded = self._excluded_from_declaration(entry)
            line_vals = self._prepare_line(
                certificate, entry, ongoing_capital_sub, excluded
            )
            certificate.write({"lines": [(0, 0, line_vals)]})

            if entry.type == "subscription" and not excluded:
                ongoing_capital_sub += entry.total_amount_line

        return partner_certificate

    def compute_declaration(self):
        self.ensure_one()
        entries = self.env["subscription.register"].search(
            [
                ("partner_id.is_company", "=", False),
                ("date", "<=", self.date_to),
                ("type", "in", ["subscription", "sell_back", "transfer"]),
            ]
        )

        subscriptions = entries.filtered(
            lambda r: r.type == "subscription" and r.date < self.date_from
        )  # noqa
        cap_prev_sub = 0.0
        for subscription in subscriptions:
            cap_prev_sub += subscription.total_amount_line

        self.previously_subscribed_capital = cap_prev_sub

        partner_cert = {}

        partner_cert = self._compute_certificates(entries, partner_cert)

        self.state = "computed"

    def validate_declaration(self):
        self.ensure_one()
        self.tax_shelter_certificates.write({"state": "validated"})
        self.state = "validated"

    def reset_declaration(self):
        self.ensure_one()
        if not self.state == "validated":
            self.tax_shelter_certificates.unlink()
            self.state = "draft"
