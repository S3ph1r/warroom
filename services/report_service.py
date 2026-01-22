
import io
import logging
from datetime import datetime
from xhtml2pdf import pisa
from services.portfolio_service import get_all_holdings, get_portfolio_summary
from services.analytics_service import get_latest_snapshot
from services.forex_service import get_exchange_rate

logger = logging.getLogger(__name__)

def generate_pdf_report() -> bytes:
    """
    Generates a PDF report of the current portfolio status.
    Returns: PDF file content as bytes.
    """
    try:
        # 1. Fetch Data
        holdings = get_all_holdings()
        
        # Calculate Totals explicitly from holdings
        total_value = 0.0
        total_cost = 0.0
        
        for h in holdings:
            val = float(h.get('current_value', 0) or 0)
            qty = float(h.get('quantity', 0) or 0)
            px_cost = float(h.get('purchase_price', 0) or 0)
            
            total_value += val
            total_cost += (qty * px_cost)

        total_profit = total_value - total_cost
        profit_pct = (total_profit / total_cost * 100) if total_cost > 0 else 0
        
        # Sort holdings by value desc
        holdings.sort(key=lambda x: float(x.get('current_value', 0) or 0), reverse=True)
        top_holdings = holdings[:25] # Increased to top 25
        
        date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        # 2. Build HTML Template
        html_content = f"""
        <html>
        <head>
            <style>
                @page {{ margin: 1.5cm; }}
                body {{ font-family: Helvetica, sans-serif; color: #333; }}
                .header {{ text-align: center; margin-bottom: 25px; border-bottom: 2px solid #444; padding-bottom: 10px; }}
                h1 {{ color: #2c3e50; margin: 0; font-size: 24px; }}
                .meta {{ font-size: 10px; color: #777; margin-top: 5px; }}
                
                .kpi-container {{ margin-bottom: 25px; background: #f8f9fa; padding: 15px; border-radius: 5px; }}
                .kpi-row {{ font-size: 14px; margin-bottom: 8px; }}
                .kpi-label {{ font-weight: bold; width: 140px; display: inline-block; }}
                .positive {{ color: #16a34a; font-weight: bold; }}
                .negative {{ color: #dc2626; font-weight: bold; }}
                
                h2 {{ background-color: #eee; padding: 8px; font-size: 14px; border-left: 5px solid #2c3e50; margin-top: 20px; }}
                
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 9px; }}
                th, td {{ border: 1px solid #e5e7eb; padding: 5px; text-align: left; vertical-align: middle; }}
                th {{ background-color: #f1f5f9; font-weight: bold; color: #475569; }}
                tr:nth-child(even) {{ background-color: #f8fafc; }}
                .text-right {{ text-align: right; }}
                
                .footer {{ position: fixed; bottom: 0; left: 0; right: 0; text-align: center; font-size: 8px; color: #aaa; border-top: 1px solid #eee; padding-top: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>WAR ROOM PORTFOLIO</h1>
                <div class="meta">Generated: {date_str}</div>
            </div>
            
            <div class="kpi-container">
                <div class="kpi-row">
                    <span class="kpi-label">Net Worth:</span>
                    <span class="kpi-value" style="font-size: 16px;">€ {total_value:,.2f}</span>
                </div>
                <div class="kpi-row">
                    <span class="kpi-label">Total Cost:</span>
                    <span class="kpi-value">€ {total_cost:,.2f}</span>
                </div>
                <div class="kpi-row">
                    <span class="kpi-label">Total P&L:</span>
                    <span class="kpi-value {('positive' if total_profit >= 0 else 'negative')}">
                        € {total_profit:,.2f} ({profit_pct:+.2f}%)
                    </span>
                </div>
                <div class="kpi-row">
                    <span class="kpi-label">Active Positions:</span>
                    <span class="kpi-value">{len(holdings)}</span>
                </div>
            </div>
            
            <h2>Holdings Overview (Top 25)</h2>
            <table>
                <thead>
                    <tr>
                        <th width="5%">#</th>
                        <th width="12%">Broker</th>
                        <th width="8%">Ticker</th>
                        <th width="30%">Name</th>
                        <th width="10%" class="text-right">Qty</th>
                        <th width="10%" class="text-right">Price</th>
                        <th width="15%" class="text-right">Value (EUR)</th>
                        <th width="10%" class="text-right">% Alloc</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for idx, h in enumerate(top_holdings):
            rank = idx + 1
            broker = h.get('broker', '').replace('_', ' ').title()
            ticker = h.get('ticker', '')
            name = h.get('name', '')
            qty = float(h.get('quantity', 0) or 0)
            
            # Using current_value logic or current_price * qty? 
            # Trust current_value from DB as it handles FX conversion in ETL usually
            val = float(h.get('current_value', 0) or 0)
            
            # Current Price (Approx from Val/Qty if price missing, or use price)
            price = float(h.get('current_price', 0) or 0)
            if price == 0 and qty > 0:
                price = val / qty # Implied price
            
            alloc = (val / total_value * 100) if total_value > 0 else 0
            
            html_content += f"""
                    <tr>
                        <td>{rank}</td>
                        <td>{broker}</td>
                        <td>{ticker}</td>
                        <td>{name[:35]}</td>
                        <td class="text-right">{qty:,.2f}</td>
                        <td class="text-right">€ {price:,.2f}</td>
                        <td class="text-right"><strong>€ {val:,.2f}</strong></td>
                        <td class="text-right">{alloc:.1f}%</td>
                    </tr>
            """
            
        html_content += """
                </tbody>
            </table>
            
            <div class="footer">
                Progetto War Room - Confidential Report
            </div>
        </body>
        </html>
        """
        
        # 3. Convert via xhtml2pdf
        pdf_file = io.BytesIO()
        pisa_status = pisa.CreatePDF(
            io.StringIO(html_content),
            dest=pdf_file
        )
        
        if pisa_status.err:
            logger.error(f"PDF Generation Error: {pisa_status.err}")
            return None
            
        pdf_file.seek(0)
        return pdf_file.getvalue()
        
    except Exception as e:
        logger.error(f"Report Generation Failed: {e}")
        return None
