
import openpyxl

def check_sheets():
    fpath = "c:/Users/chzam/OneDrive/Desktop/cerebro-patio/Cerebro/Detalle Entel.xlsx"
    wb = openpyxl.load_workbook(fpath, read_only=True)
    print(f"Sheets: {wb.sheetnames}")

if __name__ == "__main__":
    check_sheets()
