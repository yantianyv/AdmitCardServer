import argparse
import json
import os
from openpyxl import load_workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.flowables import Flowable, HRFlowable

# 定义一个Flowable类，用于绘制带有文本的矩形框
class PhotoBox(Flowable):
    def __init__(self, width, height, text=""):
        Flowable.__init__(self)
        self.width = width
        self.height = height
        self.text = text
        
    # 绘制矩形框和文本
    def draw(self):
        self.canv.setDash(2, 2)
        self.canv.rect(0, 0, self.width, self.height)
        self.canv.setDash(1, 0)
        self.canv.setFont("WenQuanYi", 10)
        text_width = self.canv.stringWidth(self.text, "WenQuanYi", 10)
        self.canv.drawString((self.width - text_width)/2, self.height/2 - 5, self.text)

# 加载配置文件
def load_config(config_name="default"):
    config_path = os.path.join("config", f"{config_name}.json")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file {config_path} not found")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

# 验证Excel文件结构
def validate_excel_structure(ws):
    if ws.cell(row=1, column=1).value != "姓名" or ws.cell(row=1, column=2).value != "身份证号":
        raise ValueError("Excel文件第一列应为'姓名'，第二列应为'身份证号'")

# 读取Excel文件中的数据
def read_excel_data(excel_path):
    wb = load_workbook(excel_path)
    ws = wb.active
    validate_excel_structure(ws)
    
    # 获取表头
    headers = [cell.value for cell in ws[1]]
    
    data = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        student = {
            "name": row[0],
            "id": row[1],
            "fields": row[2:],
            "field_headers": headers[2:]  # 保存额外字段的表头
        }
        data.append(student)
    return data

# 生成准考证
def generate_admit_card(student, config, output_dir="AdmitCards"):
    pdfmetrics.registerFont(TTFont("WenQuanYi", "fonts/wqy-microhei.ttc"))
    
    styles = getSampleStyleSheet()
    # Only modify the styles we actually use
    styles["Title"].fontName = "WenQuanYi"
    styles["Title"].fontSize = 24
    styles["Title"].textColor = colors.HexColor("#333333")
    styles["Heading1"].fontName = "WenQuanYi"
    styles["Heading2"].fontName = "WenQuanYi"
    styles["Normal"].fontName = "WenQuanYi"
    styles["Normal"].fontSize = 14
    # Add Chinese style for exam notes
    styles.add(ParagraphStyle(
        name="Chinese",
        fontName="WenQuanYi",
        fontSize=14,
        leading=16,
        spaceBefore=6,
        spaceAfter=6
    ))
    filename = f"{student['id']}-{student['name']}.pdf"
    doc = SimpleDocTemplate(
        os.path.join(output_dir, filename),
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    elements = []
    elements.append(Paragraph("准考证", styles["Title"]))
    elements.append(Spacer(1, 1*cm))
    
    # 第一部分：考生信息
    info_elements = [
        Paragraph(f"<b>考试名称:</b> {config['exam_name']}", styles["Normal"]),
        Spacer(1, 0.5*cm),  # 增加上下间距
        Paragraph(f"<b>考试地点:</b> {config['exam_location']}", styles["Normal"]),
        Spacer(1, 0.5*cm),  # 增加上下间距
        Paragraph(f"<b>姓名:</b> {student['name']}", styles["Normal"]),
        Spacer(1, 0.5*cm),  # 增加上下间距
        Paragraph(f"<b>身份证号:</b> {student['id']}", styles["Normal"]),
        Spacer(1, 0.5*cm),  # 增加上下间距
    ]
    
    # 添加额外字段
    for header, field in zip(student.get("field_headers", []), student["fields"]):
        info_elements.append(Paragraph(f"<b>{header}:</b> {field}", styles["Normal"]))
        info_elements.append(Spacer(1, 0.5*cm))  # 增加上下间距
    
    # 将第一部分放入带边框的Table
    part1_table = Table([
        [info_elements, PhotoBox(2.5*cm, 3.5*cm, "一寸照片粘贴处"), None]  # 添加None作为新的列
    ], colWidths=[10*cm, 3*cm, 1*cm])  # 调整第二列的宽度，并设置新列的宽度为1cm
    part1_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),  # 修改此处为垂直居中
        ("ALIGN", (1,0), (1,0), "RIGHT"),
        ("BOX", (0,0), (-1,-1), 1, colors.HexColor("#4a86e8")),
        ("PADDING", (0,0), (-1,-1), 16),
        ("ROUNDEDCORNERS", [4,4,4,4])
    ]))
    
    elements.append(part1_table)
    elements.append(Spacer(1, 0.5*cm))

    # 第二部分：考试时间表
    exam_info = [["科目", "考试时间"]]
    for schedule in config["exam_schedule"]:
        exam_info.append([schedule["subject"], schedule["time"]])
    exam_info.append(["", ""])


    part2_table = Table(exam_info, colWidths=[4*cm, 10*cm],rowHeights=1*cm)
    part2_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "WenQuanYi"),
        ("FONTSIZE", (0,0), (-1,-1), 14),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f5f5f5")),
        ("ALIGN", (0,0), (-1,0), "CENTER"),  # 科目列居中对齐
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),  # 所有单元格上下居中对齐
        ("BOX", (0,0), (-1,-1), 1, colors.HexColor("#4a86e8")),
        ("PADDING", (0,0), (-1,-1), 14),
        ("ROUNDEDCORNERS", [4,4,4,4]),
        ("LINEBELOW", (-1,-1), (-1,-1), 1, colors.HexColor("#4a86e8"))
    ]))
    
    elements.append(part2_table)
    elements.append(Spacer(1, 0.5*cm))
    
    # 第三部分：注意事项
    notes_elements = [Paragraph("注意事项：", styles["Heading2"])]
    for note in config["exam_notes"]:
        notes_elements.append(Paragraph(note, styles["Normal"]))
        notes_elements.append(Spacer(1, 0.5*cm))
    
    part3_table = Table([[notes_elements]], colWidths=[14*cm])
    part3_table.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 1, colors.HexColor("#4a86e8")),
        ("PADDING", (0,0), (-1,-1), 12),
        ("ROUNDEDCORNERS", [4,4,4,4])
    ]))
    
    elements.append(part3_table)
    
    # 移除文档整体边框设置
    doc.border = 0
    doc.borderPadding = 0
    doc.borderColor = None
    doc.borderStyle = None
    
    doc.build(elements)

# 主函数
def main():
    parser = argparse.ArgumentParser(description="准考证生成器")
    parser.add_argument("excel_file", help="考生信息Excel文件路径")
    parser.add_argument("-c", "--config", default="default", help="配置文件名（不带.json扩展名）")
    args = parser.parse_args()
    
    try:
        config = load_config(args.config)
        students = read_excel_data(args.excel_file)
        os.makedirs("AdmitCards", exist_ok=True)
        for student in students:
            generate_admit_card(student, config)
        print(f"成功生成{len(students)}份准考证到AdmitCards目录")
    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    main()
