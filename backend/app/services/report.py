"""Server-side PDF audit report (ReportLab)."""
from datetime import date
from xml.sax.saxutils import escape
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

def _table(head, rows):
    rows = rows or [["-"] * len(head)]
    t = Table([head] + rows, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7c5cff")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("GRID", (0, 0), (-1, -1), .3, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 8)]))
    return t

def build_pdf(R, user):
    ss, buf = getSampleStyleSheet(), BytesIO()
    inr = lambda x: f"Rs {x:,.0f}"
    clean = lambda s: s.replace("₹", "Rs ").replace("’", "'")
    grade = "ABCDE"[0 if R["hs"] >= 85 else 1 if R["hs"] >= 70 else 2 if R["hs"] >= 55 else 3 if R["hs"] >= 40 else 4]
    s = [Paragraph("SmartAudit AI - Audit Report", ss["Title"]),
         Paragraph(f"Prepared for {escape(user)} on {date.today():%d %B %Y}", ss["Normal"]), Spacer(1, 12),
         _table(["Financial health", "Transactions", "Flagged", "Exposure", "Compliance"],
                [[f"{R['hs']} (grade {grade})", R["n"], R["nfl"], inr(R["exp"]), f"{R['cs']*100:.0f}%"]]), Spacer(1, 14),
         Paragraph("Audit recommendations", ss["Heading2"])]
    s += [Paragraph(f"<b>{escape(lvl)}</b>: {escape(clean(txt))}", ss["Normal"]) for lvl, txt in R["recs"]]
    s += [Spacer(1, 10), Paragraph("Top flagged transactions", ss["Heading2"]),
          _table(["ID", "Date", "Vendor", "Employee", "Amount", "Risk", "Pattern"],
                 [[r["id"], r["d"] or "-", r["v"], r["e"], inr(r["a"]), round(r["r"] * 100), r["ty"]] for r in R["rows"][:15]]),
          Spacer(1, 10), Paragraph("Vendor trust (lowest 8)", ss["Heading2"]),
          _table(["Vendor", "Payments", "Flagged", "Trust"], [[v["name"], v["n"], v["fl"], v["sc"]] for v in R["vend"][:8]]),
          Spacer(1, 10), Paragraph("Employee risk (highest 8)", ss["Heading2"]),
          _table(["Employee", "Transactions", "Flagged", "Risk"], [[e["name"], e["n"], e["fl"], e["sc"]] for e in R["emp"][:8]]),
          Spacer(1, 10), Paragraph("Compliance", ss["Heading2"]),
          _table(["Rule", "Violations"], [[clean(c["n"]), c["f"] if c["ok"] is not None else "n/a"] for c in R["comp"]])]
    h = R.get("history")
    h = h if isinstance(h, dict) else {}
    s += [Spacer(1, 10), Paragraph("Historical vs current", ss["Heading2"])]
    if h.get("available"):
        s += [_table(["", "Historical", "Current"], [["Transactions", h["hist_n"], h["cur_n"]],
                                                     ["Period", f"{h['hist_from']} to {h['hist_to']}", f"{h['cur_from']} to {h['cur_to']}"],
                                                     ["Avg monthly spend", inr(h["hist_monthly_avg"]), inr(h["cur_monthly_avg"])]]),
              Paragraph(f"Amount deviations vs vendor history: {len(h['amount_flags'])}. Repeated invoices: {len(h['repeated_invoices'])}. "
                        f"New vendors: {h['new_vendors']}. Vendors without enough history to compare: {h['thin_vendors']}.", ss["Normal"])]
    else:
        s.append(Paragraph("Historical comparisons are unavailable: no historical transactions have been uploaded.", ss["Normal"]))
    SimpleDocTemplate(buf, pagesize=A4, title="SmartAudit AI Report").build(s)
    return buf.getvalue()
