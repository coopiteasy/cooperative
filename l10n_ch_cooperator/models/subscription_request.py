from odoo import fields, models

from . import res_partner


class SubscriptionRequest(models.Model):
    _inherit = "subscription.request"

    company_type = fields.Selection(
        selection_add=res_partner.get_company_type_selection()
    )

    def get_required_field(self):
        req_fields = super(SubscriptionRequest, self).get_required_field()
        if "iban" in req_fields:
            req_fields.remove("iban")

        return req_fields

    def check_iban(self, iban):
        if iban:
            return super(SubscriptionRequest, self).check_iban(iban)
        return True
