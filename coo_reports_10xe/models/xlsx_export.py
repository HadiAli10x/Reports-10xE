import base64
import io
import re
import zipfile
from xml.sax.saxutils import escape

from odoo import models
from odoo.exceptions import AccessError


class CooReportXlsxMixin(models.AbstractModel):
    _name = "coo.report.xlsx.mixin"
    _description = "COO Report XLSX Export Helper"

    def _check_coo_report_access(self):
        if not (
            self.env.su
            or self.env.user.has_group("coo_reports_10xe.group_coo_reports_ayesha")
        ):
            raise AccessError("You are not allowed to access the COO reporting hub.")

    def _download_xlsx(self, filename, sheets):
        self.ensure_one()
        self._check_coo_report_access()
        content = self._build_xlsx(sheets)
        attachment = self.env["ir.attachment"].sudo().create({
            "name": filename,
            "type": "binary",
            "datas": base64.b64encode(content),
            "res_model": self._name,
            "res_id": self.id,
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }

    def _build_xlsx(self, sheets):
        normalized = [self._normalize_sheet(sheet, index) for index, sheet in enumerate(sheets, 1)]
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as workbook:
            workbook.writestr("[Content_Types].xml", self._content_types(len(normalized)))
            workbook.writestr("_rels/.rels", self._root_rels())
            workbook.writestr("xl/workbook.xml", self._workbook(normalized))
            workbook.writestr("xl/_rels/workbook.xml.rels", self._workbook_rels(len(normalized)))
            workbook.writestr("xl/styles.xml", self._styles())
            for index, sheet in enumerate(normalized, 1):
                workbook.writestr(f"xl/worksheets/sheet{index}.xml", self._worksheet(sheet))
        return output.getvalue()

    def _normalize_sheet(self, sheet, index):
        name = re.sub(r"[\\/*?:\[\]]", "-", str(sheet.get("name") or f"Sheet {index}"))[:31]
        headers = list(sheet.get("headers") or [])
        rows = [list(row) for row in sheet.get("rows") or []]
        widths = list(sheet.get("widths") or [])
        if len(widths) < len(headers):
            widths.extend([20] * (len(headers) - len(widths)))
        return {
            "name": name or f"Sheet {index}",
            "title": str(sheet.get("title") or name or f"Sheet {index}"),
            "note": str(sheet.get("note") or ""),
            "headers": headers,
            "rows": rows,
            "widths": widths,
        }

    def _worksheet(self, sheet):
        header_row = 3 if sheet["note"] else 2
        data_row = header_row + 1
        cells = [self._row(1, [sheet["title"]], style=2)]
        if sheet["note"]:
            cells.append(self._row(2, [sheet["note"]], style=3))
        if sheet["headers"]:
            cells.append(self._row(header_row, sheet["headers"], style=1))
        for row_index, row in enumerate(sheet["rows"], data_row):
            cells.append(self._row(row_index, row))

        column_count = max(len(sheet["headers"]), max((len(row) for row in sheet["rows"]), default=1), 1)
        last_row = max(data_row + len(sheet["rows"]) - 1, header_row)
        last_column = self._column_name(column_count)
        columns = "".join(
            f'<col min="{index}" max="{index}" width="{max(8, min(float(width), 100))}" customWidth="1"/>'
            for index, width in enumerate(sheet["widths"][:column_count], 1)
        )
        auto_filter = (
            f'<autoFilter ref="A{header_row}:{last_column}{last_row}"/>'
            if sheet["headers"]
            else ""
        )
        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetViews><sheetView tabSelected="1" workbookViewId="0"><pane ySplit="{header_row}" topLeftCell="A{data_row}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>
  <cols>{columns}</cols>
  <sheetData>{''.join(cells)}</sheetData>
  {auto_filter}
</worksheet>'''

    def _row(self, row_index, values, style=0):
        return f'<row r="{row_index}">' + "".join(
            self._cell(row_index, column_index, value, style)
            for column_index, value in enumerate(values, 1)
        ) + "</row>"

    def _cell(self, row_index, column_index, value, style=0):
        reference = f"{self._column_name(column_index)}{row_index}"
        style_attr = f' s="{style}"' if style else ""
        if isinstance(value, bool):
            value = "Yes" if value else "No"
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return f'<c r="{reference}"{style_attr}><v>{value}</v></c>'
        text = escape(str(value or ""))
        preserve = ' xml:space="preserve"' if text != text.strip() else ""
        return f'<c r="{reference}" t="inlineStr"{style_attr}><is><t{preserve}>{text}</t></is></c>'

    def _column_name(self, index):
        name = ""
        while index:
            index, remainder = divmod(index - 1, 26)
            name = chr(65 + remainder) + name
        return name

    def _content_types(self, sheet_count):
        sheet_overrides = "".join(
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for index in range(1, sheet_count + 1)
        )
        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  {sheet_overrides}
</Types>'''

    def _root_rels(self):
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''

    def _workbook(self, sheets):
        sheet_nodes = "".join(
            f'<sheet name="{escape(sheet["name"])}" sheetId="{index}" r:id="rId{index}"/>'
            for index, sheet in enumerate(sheets, 1)
        )
        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>{sheet_nodes}</sheets>
</workbook>'''

    def _workbook_rels(self, sheet_count):
        relationships = "".join(
            f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>'
            for index in range(1, sheet_count + 1)
        )
        relationships += f'<Relationship Id="rId{sheet_count + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{relationships}</Relationships>'''

    def _styles(self):
        return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="4">
    <font><sz val="11"/><name val="Aptos"/></font>
    <font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Aptos"/></font>
    <font><b/><color rgb="FF1F4E78"/><sz val="16"/><name val="Aptos Display"/></font>
    <font><i/><color rgb="FF666666"/><sz val="10"/><name val="Aptos"/></font>
  </fonts>
  <fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF1F4E78"/><bgColor indexed="64"/></patternFill></fill></fills>
  <borders count="2"><border/><border><left style="thin"><color rgb="FFD9E2F3"/></left><right style="thin"><color rgb="FFD9E2F3"/></right><top style="thin"><color rgb="FFD9E2F3"/></top><bottom style="thin"><color rgb="FFD9E2F3"/></bottom></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="4">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment wrapText="1"/></xf>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''
