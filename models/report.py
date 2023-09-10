
from odoo import models, api, fields, exceptions, _
from datetime import date, datetime, time
from odoo.exceptions import UserError






class AnalisysReport(models.Model):
    _name="analisys.report"

    state=fields.Selection([("d","Draft"),("c","Confirmado"),("e","Enviado")],default="d",string="Estado")   

    name=fields.Char(string="Nombre")
    start_date=fields.Datetime(string="Fecha Inicio")
    end_date=fields.Datetime(string="Fecha Fin")
    resultado=fields.Float(string="Resultado",compute="get_resultado")
    taxes_ids=fields.One2many("taxes.line","analisys_id")
    test=fields.Text()

    def action_confirm(self):
        self.state="c"
        
    def action_send(self):
        self.state="e"
        
    
    
    def compute_one2many(self):
        if len(self.taxes_ids)>0:
            for line in self.taxes_ids:
                line.unlink()
        obj=self.env["account.move.line"].search([
            ("move_id.invoice_date",">=",self.start_date),
            ("move_id.invoice_date","<=",self.end_date),
            ("move_id.state","=","posted"),
            ("move_id.move_type","in",["out_invoice","in_invoice"])
        ])

        obj1=self.env["account.move.line"].search([
            ("move_id.invoice_date",">=",self.start_date),
            ("move_id.invoice_date","<=",self.end_date),
            ("move_id.state","=","posted"),
            ("move_id.move_type","in",["out_invoice","in_invoice"]),
            ("tax_ids", "=", False)
        ])
        vals=[]
        tax=obj.mapped("tax_ids")

        u_tax=[]
        for line in tax:
            if line not in u_tax:
                u_tax.append(line)
        venta=obj.filtered(lambda x:x.move_id.move_type=="out_invoice")
        compra=obj.filtered(lambda x:x.move_id.move_type=="in_invoice")
        exento=obj.filtered(lambda x: not x.tax_ids)
        for line in u_tax:
            venta_net=[]
            venta_imp=[]
            compra_net=[]
            compra_imp=[]
           
            for record in venta:
                if line.id in record.tax_ids.ids:
                    venta_net.append(record.price_subtotal)
                    venta_imp.append(record.price_subtotal*line.amount/100)
            for record in compra:
                if line.id in record.tax_ids.ids:
                    compra_net.append(record.price_subtotal)
                    compra_imp.append(record.price_subtotal*line.amount/100)
            
            vals.append({
                        'analisys_id':self.id,
                        'tax_id':line.id,
                        'venta_net':sum(venta_net),
                        'venta_tax':sum(venta_imp),
                        'compra_net':sum(compra_net),
                        'compra_tax':sum(compra_imp),

                        })
        excomp=[]
        exvent=[]
        for line1 in obj1:
            if line1.move_id.move_type=="out_invoice" and line1.price_total>0 and not line1.tax_line_id:
                exvent.append(line1.price_total)
            elif line1.move_id.move_type=="in_invoice" and line1.price_total>0 and not line1.tax_line_id:# and line1.price_subtotal==line1.price_total:
                excomp.append(line1.price_total)
        
        vals.append({
            'analisys_id':self.id,
            'tax_id':False,
            'venta_net':sum(exvent),
            'venta_tax':0,
            'compra_net':sum(excomp),
            'compra_tax':0,
        }) 

        self.test=str(obj1)+ str(excomp)+ str(exvent)
        
        vals2=[]        
        for x in vals:
            if x not in vals2:
                vals2.append(x)

        for i in vals:
            self.taxes_ids=[(0,0,i)]

    def get_resultado(self):
        
        for record in self:
            res=[]
            for line in record.taxes_ids:
                res.append(line.dif)
            if res:
                record.resultado=sum(res)
            else:
                record.resultado=0

    
class TaxesLine(models.Model):
    _name="taxes.line"

    analisys_id=fields.Many2one("analisys.report")
    tax_id=fields.Many2one("account.tax",string="Impuesto")
    venta_net=fields.Float(string="Venta neto")
    venta_tax=fields.Float(string="Venta Impuesto")
    compra_net=fields.Float(string="Compra neto")
    compra_tax=fields.Float(string="Compra Impuesto")
    dif=fields.Float(string="Dif impuesto",compute="get_dif")
    
    def get_dif(self):
        for line in self:
            
            line.dif=line.venta_tax-line.compra_tax
            



