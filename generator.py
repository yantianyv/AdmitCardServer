import argparse
import json
import os
import sys
from openpyxl import load_workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.flowables import Flowable, HRFlowable

# 默认配置模板
default_config = {
    "exam_name": "默认考试",
    "exam_location": "默认考试地点",
    "settings": {"render_photo_frame": True},
    "exam_schedule": [{"subject": "科目", "time": "时间"}],
    "exam_notes": ["注意事项"],
}

# 全局缓存字体和样式
_font_registered = False
_styles_cache = None

def _init_global_styles():
    global _font_registered, _styles_cache
    if not _font_registered:
        pdfmetrics.registerFont(TTFont("WenQuanYi", "fonts/wqy-microhei.ttc"))
        _font_registered = True
    
    if _styles_cache is None:
        styles = getSampleStyleSheet()
        styles["Title"].fontName = "WenQuanYi"
        styles["Title"].fontSize = 24
        styles["Title"].textColor = colors.HexColor("#333333")
        styles["Heading1"].fontName = "WenQuanYi"
        styles["Heading2"].fontName = "WenQuanYi"
        styles["Normal"].fontName = "WenQuanYi"
        styles["Normal"].fontSize = 14
        styles.add(
            ParagraphStyle(
                name="Chinese",
                fontName="WenQuanYi",
                fontSize=14,
                leading=20,
                spaceBefore=6,
                spaceAfter=6,
            )
        )
        _styles_cache = styles
    return _styles_cache


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
        self.canv.drawString(
            (self.width - text_width) / 2, self.height / 2 - 5, self.text
        )


# 加载配置文件
def load_config(config_name="default"):
    config_path = os.path.join("config", f"{config_name}.json")

    global default_config

    if not os.path.exists(config_path):
        # 创建配置文件目录
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        # 生成默认配置文件
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        # 用黄色字体输出警告
        print("\033[1;33m警告：配置文件不存在，已生成默认配置文件。\033[0m")
        return default_config

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# 验证Excel文件结构
def validate_excel_structure(ws):
    if (
        ws.cell(row=1, column=1).value != "姓名"
        or ws.cell(row=1, column=2).value != "身份证号"
    ):
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
            "field_headers": headers[2:],  # 保存额外字段的表头
        }
        data.append(student)
    return data


# 生成准考证
def generate_admit_card(student, config, output_dir="AdmitCards"):
    styles = _init_global_styles()
    filename = f"{student['id']}-{student['name']}.pdf"
    doc = SimpleDocTemplate(
        os.path.join(output_dir, filename),
        pagesize=A4,
        leftMargin=1 * cm,
        rightMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm,
    )

    elements = []

    # 第一部分：考生信息
    info_elements = []

    # 添加考试名称（独立段落）
    if config.get("exam_name"):
        exam_name_style = ParagraphStyle(
            "ExamNameStyle",
            parent=styles["Title"],
            alignment=1,  # 1表示居中对齐
            fontSize=18,
        )
        elements.append(Paragraph(f"{config['exam_name']}", exam_name_style))

    elements.append(Paragraph("准考证", styles["Title"]))

    # 添加其他信息到表格
    if config.get("exam_location"):
        info_elements.append(
            Paragraph(f"<b>考试地点:</b> {config['exam_location']}", styles["Normal"])
        )
        info_elements.append(Spacer(1, 0.5 * cm))

    # 检查并添加学生基本信息
    if not student.get("name"):
        print(
            f"\033[1;33m警告：身份证号 {student['id']} 的姓名为空，已隐藏该字段\033[0m"
        )
    else:
        info_elements.append(
            Paragraph(f"<b>姓名:</b> {student['name']}", styles["Normal"])
        )
        info_elements.append(Spacer(1, 0.5 * cm))

    if not student.get("id"):
        print(
            f"\033[1;33m警告：考生 {student['name']} 的身份证号为空，已隐藏该字段\033[0m"
        )
    else:
        info_elements.append(
            Paragraph(f"<b>身份证号:</b> {student['id']}", styles["Normal"])
        )
        info_elements.append(Spacer(1, 0.5 * cm))

    # 添加额外字段
    for header, field in zip(student.get("field_headers", []), student["fields"]):
        if not field:
            print(
                f"\033[1;33m警告：考生 {student['name']} 的字段 '{header}' 为空，已隐藏该字段\033[0m"
            )
        else:
            info_elements.append(
                Paragraph(f"<b>{header}:</b> {field}", styles["Normal"])
            )
            info_elements.append(Spacer(1, 0.5 * cm))  # 增加上下间距

    # 获取照片框渲染设置
    render_photo = config["settings"]["render_photo_frame"]

    # 根据设置构建表格
    if render_photo:
        part1_table = Table(
            [[info_elements, PhotoBox(2.5 * cm, 3.5 * cm, "一寸照片粘贴处"), None]],
            colWidths=[10 * cm, 3 * cm, 1 * cm],
        )
    else:
        part1_table = Table([[info_elements, None]], colWidths=[13 * cm, 1 * cm])

    part1_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),  # 设置所有单元格内容居中
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#4a86e8")),
                ("PADDING", (0, 0), (-1, -1), 16),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]
        )
    )

    elements.append(part1_table)
    elements.append(Spacer(1, 0.5 * cm))

    # 第二部分：考试时间表
    exam_info = [["科目", "考试时间"]]
    for schedule in config["exam_schedule"]:
        exam_info.append([schedule["subject"], schedule["time"]])
    exam_info.append(["", ""])

    # 设置行高，最后一行高度为0.5cm
    row_heights = [1 * cm] * (len(exam_info) - 1) + [0.2 * cm]
    part2_table = Table(exam_info, colWidths=[4 * cm, 10 * cm], rowHeights=row_heights)
    part2_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "WenQuanYi"),
                ("FONTSIZE", (0, 0), (-1, -1), 14),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f5f5f5")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),  # 所有单元格内容居中对齐
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),  # 所有单元格上下居中对齐
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#4a86e8")),
                ("PADDING", (0, 0), (-1, -1), 14),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
                ("LINEBELOW", (-1, -1), (-1, -1), 1, colors.HexColor("#4a86e8")),
            ]
        )
    )

    elements.append(part2_table)
    elements.append(Spacer(1, 0.5 * cm))

    # 第三部分：注意事项
    notes_elements = [Paragraph("注意事项：", styles["Heading2"])]
    for index, note in enumerate(config["exam_notes"], 1):
        note_style = ParagraphStyle(
            "NoteStyle",
            parent=styles["Normal"],
            leading=18,  # 行高
            leftIndent=24,  # 整体左缩进（单位：点）
            firstLineIndent=-12,  # 首行缩进（负值表示向左突出）
        )
        notes_elements.append(Paragraph(f"<b>{index}.</b> {note}", note_style))

    part3_table = Table([[notes_elements]], colWidths=[14 * cm])
    part3_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#4a86e8")),
                ("PADDING", (0, 0), (-1, -1), 12),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]
        )
    )

    elements.append(part3_table)

    # 移除文档整体边框设置
    doc.border = 0
    doc.borderPadding = 0
    doc.borderColor = None
    doc.borderStyle = None

    # 检查内容高度是否超过一页
    content_height = 0
    for e in elements:
        wrapped = e.wrap(doc.width, doc.height)
        content_height += wrapped[1] if wrapped else 0

    if content_height > doc.height:
        print(f"\033[1;33m警告：考生 {student['name']} (身份证号: {student['id']}) 的准考证内容过长（{content_height:.1f}点），可能无法在一页内完整显示。建议减少内容或调整格式。\033[0m")

    doc.build(elements)


# 主函数
def main():
    # 确保必要目录存在
    os.makedirs("config", exist_ok=True)
    os.makedirs("AdmitCards", exist_ok=True)

    if not os.path.exists(os.path.join("config", "default.json")):
        # 创建配置文件目录
        os.makedirs(
            os.path.dirname(os.path.join("config", "default.json")), exist_ok=True
        )
        # 生成默认配置文件
        with open(os.path.join("config", "default.json"), "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
        # 用黄色字体输出警告
        print("\033[1;33m初次使用，已帮您生成默认配置文件，请修改后再次启动\033[0m")
        return default_config

    # 自定义错误处理类
    class CustomArgumentParser(argparse.ArgumentParser):
        def error(self, message):
            if "the following arguments are required" in message:
                print("请指定考生信息Excel文件路径")
                self.exit(2)
            else:
                super().error(message)

    parser = CustomArgumentParser(description="准考证生成器", add_help=False)
    parser.add_argument("excel_file", help="考生信息Excel文件路径")
    parser.add_argument(
        "-c", "--config", default="default", help="配置文件名（不带.json扩展名）"
    )
    parser.add_argument("-h", "--help", action="help", help="显示帮助信息并退出")

    args = parser.parse_args()

    try:
        # 加载配置（会自动创建默认配置）
        config = load_config(args.config)

        # 检查config字段
        if not config.get('exam_name'):
            print("\033[1;33m警告：考试名称为空，将隐藏该字段\033[0m")
        if not config.get('exam_location'):
            print("\033[1;33m警告：考试地点为空，将隐藏该字段\033[0m")

        # 检查是否有Excel文件参数
        if not hasattr(args, 'excel_file') or not args.excel_file:
            print("请指定考生信息Excel文件路径")
            return

        students = read_excel_data(args.excel_file)
        total = len(students)
        print(f"开始生成{total}份准考证...")

        for i, student in enumerate(students, 1):
            generate_admit_card(student, config)
            progress = int(i / total * 100)
            # 生成字符进度条 (20个字符长度)
            progress_bar = "#" * (progress // 5) + "_" * (20 - progress // 5)
            sys.stdout.write(f"\r进度: {progress_bar} {progress}% ({i}/{total})")
            sys.stdout.flush()

        print(f"\n成功生成{total}份准考证到AdmitCards目录")
    except Exception as e:
        print(f"错误: {str(e)}")
        if isinstance(e, FileNotFoundError) and str(e).endswith(".json not found"):
            print("已自动创建默认配置文件，请按需修改后重新运行程序")


if __name__ == "__main__":
    main()
