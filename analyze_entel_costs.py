
import pandas as pd
import numpy as np

def analyze_entel():
    fpath = "c:/Users/chzam/OneDrive/Desktop/cerebro-patio/Cerebro/Detalle Entel.xlsx"
    print(f"Analyzing: {fpath}")
    
    print(f"Analyzing (Multi-Sheet): {fpath}")
    
    xls = pd.ExcelFile(fpath)
    all_sheets = []
    
    for sheet in xls.sheet_names:
        print(f"Reading Sheet: {sheet}")
        try:
            temp_df = pd.read_excel(xls, sheet_name=sheet)
            # Ensure 'Mes' column exists or fill it with sheet name
            # Map columns first to be safe
            temp_df.columns = [str(c).strip() for c in temp_df.columns]
            
            # Check for Date Column
            date_col_candidate = None
            if 'Mes' in temp_df.columns:
                date_col_candidate = 'Mes'
            elif len(temp_df.columns) > 8:
                 date_col_candidate = temp_df.columns[8]
            
            if date_col_candidate and date_col_candidate in temp_df.columns:
                # If column exists but is empty/NaN, fill with sheet name
                temp_df['Mes_Unified'] = temp_df[date_col_candidate].fillna(sheet)
            else:
                temp_df['Mes_Unified'] = sheet
                
            all_sheets.append(temp_df)
            
        except Exception as e:
            print(f"Error reading {sheet}: {e}")
            
    if not all_sheets:
        print("No data found.")
        return

    df = pd.concat(all_sheets, ignore_index=True)
    
    # 1. Map Columns
    # ID column missing in current file version. Using Plan as grouper.
    print(f"Columns found (Combined): {list(df.columns)}")
    
    plan_col = df.columns[0] # 'Plan' (or 'Tipo de Servicio')
    
    # Identify Header Names dynamically if possible, or stick to Index Logic
    # Verify by Index if names vary
    total_col = df.columns[7]
    extras_col = df.columns[4]
    fixed_col = df.columns[1]
    date_col = 'Mes_Unified' # Use our unified column
    
    print(f"Mapped: Plan='{plan_col}', Total='{total_col}', Extras='{extras_col}', Date='{date_col}'")
    
    # 2. Clean Data
    num_cols = [total_col, extras_col, fixed_col]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
        
    line_count = len(df)
    print(f"Total Records (Implied Lines): {line_count}")
    
    # 3. Aggregations (Evolution)
    monthly_stats = df.groupby(date_col)[[total_col, extras_col, fixed_col]].sum().reset_index()
    monthly_counts = df.groupby(date_col)[plan_col].count().reset_index().rename(columns={plan_col: 'Lineas'})
    
    monthly_stats = pd.merge(monthly_stats, monthly_counts, on=date_col)
    
    month_map = {
        'Enero': 1, 'Febrero': 2, 'Marzo': 3, 'Abril': 4, 'Mayo': 5, 'Junio': 6,
        'Julio': 7, 'Agosto': 8, 'Septiembre': 9, 'Octubre': 10, 'Noviembre': 11, 'Diciembre': 12,
        'Sep': 9, 'Oct': 10, 'Nov': 11 
    }
    monthly_stats['MonthNum'] = monthly_stats[date_col].map(month_map).fillna(0)
    monthly_stats = monthly_stats.sort_values('MonthNum')
    
    print("\n--- EVOLUTION BY MONTH ---")
    print(monthly_stats[[date_col, 'Lineas', total_col, extras_col]].to_string(index=False))
    
    # 4. Alerts
    # High Extras (> 10%)
    high_extras = df[df[extras_col] > 0.1 * df[total_col]]
    print(f"\n--- ALERTS ---")
    if not high_extras.empty:
        print(f"High Extras detected in {len(high_extras)} records.")
        
    # 5. Global Summary
    total_spend = df[total_col].sum()
    total_extras = df[extras_col].sum()
    avg_per_line = total_spend / line_count if line_count else 0
    
    summary_text = f"""
--- GLOBAL SUMMARY ---
Total Records: {line_count}
Total Spend: ${total_spend:,.0f}
Total Extras: ${total_extras:,.0f} ({(total_extras/total_spend)*100:.1f}%)
Avg Cost per Record: ${avg_per_line:,.0f}

--- EVOLUTION ---
{monthly_stats[[date_col, 'Lineas', total_col, extras_col]].to_string(index=False)}

--- ALERTS ---
High Extras Records: {len(high_extras)}
"""
    # Breakdown by Plan & Report
    # Ensure Plan Stats is calculated
    plan_stats = df.groupby(plan_col)[[total_col, 'Lineas']].sum() if 'Lineas' in df else df.groupby(plan_col)[total_col].agg(['sum', 'count']).rename(columns={'sum': 'Total Cost', 'count': 'Lineas'})
    plan_stats['% of Total'] = (plan_stats['Total Cost'] / total_spend) * 100
    plan_stats = plan_stats.sort_values('Total Cost', ascending=False)

    summary_text += f"""
--- BREAKDOWN BY PLAN ---
{plan_stats.to_string()}
"""
    print(summary_text)
    
    with open("outputs/entel_final_summary.txt", "w", encoding="utf-8") as f:
        f.write(summary_text)

    out_file = "outputs/analisis_entel_final.xlsx"
    with pd.ExcelWriter(out_file) as writer:
        df.to_excel(writer, sheet_name="Data Raw", index=False)
        monthly_stats.to_excel(writer, sheet_name="Evolucion Mensual", index=False)
        plan_stats.to_excel(writer, sheet_name="Por Plan")
        
    print(f"Report Generated: {out_file}")

if __name__ == "__main__":
    analyze_entel()
