import io
import csv
from typing import Optional

from openpyxl import Workbook


class ExportService:
    """数据导出服务"""

    def export_csv(self, combinations: list[dict], param_keys: list[str]) -> str:
        """导出为CSV字符串"""
        output = io.StringIO()
        writer = csv.writer(output)

        # 表头
        header = ["index"] + param_keys
        writer.writerow(header)

        # 数据行
        for combo in combinations:
            row = [combo.get("index", "")]
            for key in param_keys:
                value = combo.get("combination_data", {}).get(key, "")
                if isinstance(value, list):
                    value = str(value)
                row.append(value)
            writer.writerow(row)

        return output.getvalue()

    def export_xlsx(self, combinations: list[dict], param_keys: list[str]) -> bytes:
        """导出为Excel字节"""
        wb = Workbook()
        ws = wb.active
        ws.title = "参数组合表"

        # 表头
        header = ["index"] + param_keys
        ws.append(header)

        # 数据行
        for combo in combinations:
            row = [combo.get("index", "")]
            for key in param_keys:
                value = combo.get("combination_data", {}).get(key, "")
                if isinstance(value, list):
                    value = str(value)
                row.append(value)
            ws.append(row)

        # 自动调整列宽
        for col in ws.columns:
            max_length = 0
            column_letter = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width

        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()


export_service = ExportService()
