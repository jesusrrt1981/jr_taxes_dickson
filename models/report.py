
from odoo import models, api, fields, exceptions, _
from datetime import date, datetime, time
from odoo.exceptions import UserError
import xlwt
from xlwt import easyxf
from io import StringIO, BytesIO
import io
import base64






class AnalisysReport(models.Model):
    _name="analisys.report"

    state=fields.Selection([("d","Draft"),("c","Confirmado"),("e","Enviado")],default="d",string="Estado")   

    name=fields.Char(string="Nombre")
    start_date=fields.Datetime(string="Fecha Inicio")
    end_date=fields.Datetime(string="Fecha Fin")
    resultado=fields.Float(string="Resultado",compute="get_resultado")
    taxes_ids=fields.One2many("taxes.line","analisys_id")
    test=fields.Text()
    excel_file=fields.Binary(string="Excel")
    file_name = fields.Char('Excel File')

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

        
        
        vals2=[]        
        for x in vals:
            if x not in vals2:
                vals2.append(x)

        for i in vals:
            self.taxes_ids=[(0,0,i)]
        self.export_stock_ledger()

    def get_resultado(self):
        
        for record in self:
            res=[]
            for line in record.taxes_ids:
                res.append(line.dif)
            if res:
                record.resultado=sum(res)
            else:
                record.resultado=0

    def export_stock_ledger(self):
        workbook = xlwt.Workbook()
        filename = 'Taxes.xls'
        # Style
        main_header_style = easyxf('font:height 400;pattern: pattern solid, fore_color gray25;'
                                'align: horiz center;font: color black; font:bold True;'
                                "borders: top thin,left thin,right thin,bottom thin")

        header_style = easyxf('font:height 200;pattern: pattern solid, fore_color gray25;'
                            'align: horiz center;font: color black; font:bold True;'
                            "borders: top thin,left thin,right thin,bottom thin")

        group_style = easyxf('font:height 200;pattern: pattern solid, fore_color gray25;'
                            'align: horiz left;font: color black; font:bold True;'
                            "borders: top thin,left thin,right thin,bottom thin")

        text_left = easyxf('font:height 150; align: horiz left;' "borders: top thin,bottom thin")
        text_right_bold = easyxf('font:height 200; align: horiz right;font:bold True;' "borders: top thin,bottom thin")
        text_right_bold1 = easyxf('font:height 200; align: horiz right;font:bold True;' "borders: top thin,bottom thin", num_format_str='0.00')
        text_center = easyxf('font:height 150; align: horiz center;' "borders: top thin,bottom thin")
        text_right = easyxf('font:height 150; align: horiz right;' "borders: top thin,bottom thin",
                            num_format_str='0.00')

        worksheet = []
        
        worksheet.append(1)
        work=0
        worksheet[work] = workbook.add_sheet("Taxes")
        
        for i in range(0, 12):
            worksheet[work].col(i).width = 140 * 30

        worksheet[work].write_merge(0, 1, 0, 9, 'REPORTE IMPUESTOS', main_header_style)
        worksheet[work].write_merge(2, 3, 0, 9, 'DICKSON', main_header_style)
      
        worksheet[work].write(5, 2, 'Fecha Inicio', header_style)
        worksheet[work].write(5, 4, 'Fecha Fin', header_style)
        worksheet[work].write(5, 3, str(self.start_date), text_center)
        worksheet[work].write(5, 5, str(self.end_date), text_center)

        obj=self.env["account.move"].search([
            ("invoice_date",">=",self.start_date),
            ("invoice_date","<=",self.end_date),
            ("state","=","posted"),
            ("move_type","=","in_invoice"),
            #("tax_line_id","=",False),
            #("tax_ids", "!=",False),
            #("price_total", ">",0)
        ])

        obj1=self.env["account.move"].search([
            ("invoice_date",">=",self.start_date),
            ("invoice_date","<=",self.end_date),
            ("state","=","posted"),
            ("move_type","=","out_invoice"),
            #("tax_ids", "=", False),
            #("tax_line_id","=",False),
            #("price_total", ">",0)
        ])
        tags=["Fecha","Cliente","Factura","Ventas Gravadas"]
        tags1=["Fecha","Cliente","Factura","Compras Gravadas"]
        venta_imp_tax=obj1.mapped("invoice_line_ids.tax_ids.name")
        compras_imp_tax=obj.mapped("invoice_line_ids.tax_ids.name")
        imp_ventas=[]
        imp_compras=[]
        for i in venta_imp_tax:
            if i not in imp_ventas and i != False:
                imp_ventas.append(i)
        for j in imp_ventas:
            tags.append(j)
        tags.append("Sin impuesto")
        tags.append("Total Factura")

        for i in compras_imp_tax:
            if i not in imp_compras and i != False:
                imp_compras.append(i)
        for j in imp_compras:
            tags1.append(j)
        tags1.append("Sin impuesto")
        tags1.append("Total Factura")
        

       

        
        r= 8
        worksheet[work].write_merge(7, 7, 0, 9, 'VENTAS', main_header_style)
        c = 1
        for tag in tags:
            worksheet[work].write(r, c, tag, header_style)
            c+=1
        

        
        
        

        r+=1
        for line in obj1:
            
            
            c=1
            worksheet[work].write(r, c, str(line.invoice_date), text_left)
            c+=1
            worksheet[work].write(r,c,line.partner_id.name, text_left)
          
            c += 1
            worksheet[work].write(r,c,line.name, text_left)
            c += 1
            worksheet[work].write(r,c,line.amount_untaxed, text_left)
            impu={}
            for inv in line.invoice_line_ids:
                if not inv.tax_line_id:
                    if len(inv.tax_ids)>1:
                        for tax in inv.tax_ids:
                            for head in tags:
                                if tax.name==head:
                                    if head not in impu:
                                        impu.update({head:inv.price_subtotal*tax.amount/100})
                                    else:
                                        impu[head]+=inv.price_subtotal*tax.amount/100
                        for heade in tags:
                            if heade in impu:
                                worksheet[work].write(r, tags.index(heade)+1,impu.get("heade"),  text_right)
                        
                    elif len(inv.tax_ids)==1:
                        for head in tags:
                            if inv.tax_ids.name==head:
                                if head not in impu:
                                        impu.update({head:inv.price_subtotal*inv.tax_ids.amount/100})
                                else:
                                    impu[head]+=inv.price_subtotal*inv.tax_ids.amount/100

            for heade in tags:
                        if heade in impu:
                            worksheet[work].write(r, tags.index(heade)+1,impu.get("heade"),  text_right)
                        elif heade =="sin impuesto":
                            worksheet[work].write(r, tags.index(heade)+1,0,  text_right)

            worksheet[work].write(r, len(tags),line.amount_total,  text_right)
            r+=1

        worksheet[work].write_merge(r+2, r+2, 0, 9, 'COMPRAS', main_header_style)

        r+=3

        for tag3 in tags1:
            worksheet[work].write(r, c, tag3, header_style)
            c+=1
        r+=1
        for line in obj:
            
            
            c=1
            worksheet[work].write(r, c, str(line.invoice_date), text_left)
            c+=1
            worksheet[work].write(r,c,line.partner_id.name, text_left)
         
            c += 1
            worksheet[work].write(r,c,line.name, text_left)
            c += 1
            worksheet[work].write(r,c,line.amount_untaxed, text_left)
            impu1={}
            for inv in line.invoice_line_ids:
                if not inv.tax_line_id:
                    if len(inv.tax_ids)>1:
                        for tax in inv.tax_ids:
                            for head in tags1:
                                if tax.name==head:
                                    if head not in impu1:
                                        impu.update({head:inv.price_subtotal*tax.amount/100})
                                    else:
                                        impu1[head]+=inv.price_subtotal*tax.amount/100
                        for heade in tags1:
                            if heade in impu1:
                                worksheet[work].write(r, tags1.index(heade)+1,impu1.get("heade"),  text_right)
                        
                    elif len(inv.tax_ids)==1:
                        for head in tags1:
                            if inv.tax_ids.name==head:
                                if head not in impu1:
                                        impu1.update({head:inv.price_subtotal*inv.tax_ids.amount/100})
                                else:
                                    impu1[head]+=inv.price_subtotal*inv.tax_ids.amount/100

                for heade in tags1:
                            if heade in impu1:
                                worksheet[work].write(r, tags1.index(heade)+1,impu1.get("heade"),  text_right)
                            elif heade =="sin impuesto":
                                worksheet[work].write(r, tags1.index(heade)+1,0,  text_right)

                worksheet[work].write(r, len(tags1),line.amount_total,  text_right)
                r+=1
        

        fp = io.BytesIO()
        workbook.save(fp)
        export_id = self.write(
            {'excel_file': base64.encodestring(fp.getvalue()), 'file_name': filename})
        fp.close()

        

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
            



