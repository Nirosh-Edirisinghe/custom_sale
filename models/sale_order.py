from email.policy import default

from odoo import models, fields, api
from datetime import date
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    total_credit_amount = fields.Float(string="Customer credit", compute="_compute_total_credit")
    credit_limit_exceeded = fields.Boolean(compute="_compute_total_credit")
    approval_status = fields.Selection([
        ('pending', 'Pending Approval'),
        ('waiting', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='pending', string="Approval Status", tracking=True)

    @api.depends('partner_id')
    def _compute_total_credit(self):
        today = fields.Date.today()

        for order in self:
            total_credit = 0
            if order.partner_id:
                invoices = self.env['account.move'].search([
                    ('partner_id', '=', order.partner_id.id),
                    ('move_type', '=', 'out_invoice'),
                    ('payment_state', '!=', 'paid'),
                    ('invoice_date_due', '<', today),
                    ('state', '=', 'posted')
                ])

                for invoice in invoices:
                    total_credit += invoice.amount_residual

            order.total_credit_amount = total_credit
            order.credit_limit_exceeded = total_credit > 20000

    def action_request_approval(self):
        for order in self:
            order.approval_status = 'waiting'

            activity_type = self.env.ref('mail.mail_activity_data_todo')
            approvers = self.env.ref('custom_sale.group_sale_order_admin').users

            if not approvers:
                raise UserError("No approver users found!")

            for user in approvers:
                self.env['mail.activity'].create({
                    'activity_type_id': activity_type.id,
                    'note': f"Sales Order {order.name} requires your approval due to credit limit exceeded.",
                    'res_id': order.id,
                    'res_model_id': self.env['ir.model'].sudo()._get('sale.order').id,
                    'user_id': user.id,
                    'summary': 'Sales Order Approval Required',
                })


    def action_approve_order(self):
        for order in self:
            order.approval_status = 'approved'

            # Mark activities done
            activities = self.env['mail.activity'].search([
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', order.id)
            ])
            activities.action_done()

            order.message_post(body="Order approved by Sales Manager.")

            order.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                user_id=order.create_uid.id,
                summary="Order Approved",
                note=f"Your order {order.name} has been approved and is ready for confirmation."
            )

    def action_reject_order(self):
        for order in self:
            order.approval_status = 'rejected'

            activities = self.env['mail.activity'].search([
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', order.id)
            ])
            activities.action_done()

            self.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                user_id=order.create_uid.id,
                summary="Order Rejected",
                note=f"Your order {order.name} was rejected. Please review and resubmit."
            )
