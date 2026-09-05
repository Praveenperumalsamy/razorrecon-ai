import os
import random
import json
import pandas as pd
from datetime import datetime, timedelta

def generate_data():
    random.seed(42)
    output_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Data structures
    bank_txs = []
    settlements = []
    ledger = []
    refunds = []
    chargebacks = []
    ground_truth = []
    
    start_date = datetime(2024, 8, 1)
    
    # Customers
    customers = [f"CUS_{str(i).zfill(4)}" for i in range(1, 151)]
    
    # Generate 100 base transactions
    for i in range(1, 101):
        tx_id = f"BTX_{str(i).zfill(4)}"
        pay_id = f"PAY_{str(i).zfill(4)}"
        order_id = f"ORD_{str(i+1000).zfill(4)}"
        
        # Random date in Aug-Sep 2024
        days_add = random.randint(0, 60)
        tx_date = start_date + timedelta(days=days_add)
        tx_date_str = tx_date.strftime("%Y-%m-%d")
        
        # Amount
        amount = round(random.uniform(500, 50000), 2)
        
        # Customer
        customer = random.choice(customers)
        
        # Ground Truth Record
        gt_record = {
            "payment_id": pay_id,
            "bank_tx_id": tx_id,
            "settlement_id": f"STL_{str(i).zfill(4)}",
            "ledger_id": f"LED_{str(i).zfill(4)}",
            "status": "exact_match",
            "anomalies": []
        }
        
        # Bank Record
        bank_tx = {
            "transaction_id": tx_id,
            "bank_reference": f"BNKREF_{random.randint(10000, 99999)}",
            "transaction_date": tx_date_str,
            "amount": amount,
            "currency": "INR" if random.random() > 0.05 else "USD",
            "transaction_type": "payment",
            "customer_reference": customer,
            "status": "completed"
        }
        
        # Settlement Record (defaults to exact match)
        stl_date = tx_date + timedelta(days=random.randint(1, 3))
        fee = round(amount * random.uniform(0.02, 0.025), 2)
        tax = round(fee * 0.18, 2)
        net_amount = amount - fee - tax
        
        settlement = {
            "settlement_id": f"STL_{str(i).zfill(4)}",
            "payment_id": pay_id,
            "settlement_date": stl_date.strftime("%Y-%m-%d"),
            "gross_amount": amount,
            "fee": fee,
            "tax": tax,
            "net_amount": net_amount,
            "status": "processed"
        }
        
        # Ledger Record
        ledger_rec = {
            "ledger_id": f"LED_{str(i).zfill(4)}",
            "order_id": order_id,
            "payment_id": pay_id,
            "transaction_date": tx_date_str,
            "expected_amount": amount,
            "recorded_amount": amount,
            "customer_id": customer,
            "status": "confirmed"
        }
        
        # INJECT ANOMALIES
        
        # ~8 amount mismatches
        if 71 <= i <= 78:
            diff = round(random.uniform(0.01, 5.00), 2)
            ledger_rec["recorded_amount"] = amount - diff
            gt_record["status"] = "anomaly"
            gt_record["anomalies"].append("amount_mismatch")
            
        # ~5 date mismatches
        elif 79 <= i <= 83:
            settlement["settlement_date"] = (tx_date + timedelta(days=random.randint(5, 10))).strftime("%Y-%m-%d")
            gt_record["status"] = "anomaly"
            gt_record["anomalies"].append("date_mismatch")
            
        # ~5 missing in settlement
        elif 84 <= i <= 88:
            settlement = None
            gt_record["status"] = "anomaly"
            gt_record["anomalies"].append("missing_in_settlement")
            
        # ~3 missing in ledger
        elif 89 <= i <= 91:
            ledger_rec = None
            gt_record["status"] = "anomaly"
            gt_record["anomalies"].append("missing_in_ledger")
            
        # ~3 duplicates in ledger
        elif 92 <= i <= 94:
            # We add the original ledger rec, plus a duplicate below
            ledger_rec2 = ledger_rec.copy()
            ledger_rec2["ledger_id"] = f"LED_{str(i+100).zfill(4)}"
            ledger_rec2["recorded_amount"] = amount - 1.0
            ledger.append(ledger_rec2)
            gt_record["status"] = "anomaly"
            gt_record["anomalies"].append("duplicate_in_ledger")
            
        # ~3 formatting differences
        elif 95 <= i <= 97:
            ledger_rec["payment_id"] = pay_id.lower() + " "
            gt_record["status"] = "anomaly"
            gt_record["anomalies"].append("formatting_difference")
            
        # ~2 partial settlements
        elif 98 <= i <= 99:
            settlement["net_amount"] = settlement["net_amount"] - round(random.uniform(10, 50), 2)
            gt_record["status"] = "anomaly"
            gt_record["anomalies"].append("partial_settlement")
            
        # ~1 fee mismatch
        elif i == 100:
            settlement["fee"] = settlement["fee"] + 5.0
            gt_record["status"] = "anomaly"
            gt_record["anomalies"].append("fee_mismatch")
            
        # Add to lists
        bank_txs.append(bank_tx)
        if settlement:
            settlements.append(settlement)
        if ledger_rec:
            ledger.append(ledger_rec)
        ground_truth.append(gt_record)
            
    # Add refunds (8 records)
    for i in range(1, 9):
        target = bank_txs[i] # Pick first 8
        refunds.append({
            "refund_id": f"RFD_{str(i).zfill(4)}",
            "payment_id": f"PAY_{target['transaction_id'].split('_')[1]}",
            "refund_date": (datetime.strptime(target["transaction_date"], "%Y-%m-%d") + timedelta(days=random.randint(1, 14))).strftime("%Y-%m-%d"),
            "refund_amount": target["amount"],
            "reason": random.choice(["product_return", "customer_request", "defective_item"]),
            "status": "processed"
        })
        
    # Add chargebacks (4 records)
    for i in range(10, 14):
        target = bank_txs[i]
        chargebacks.append({
            "chargeback_id": f"CHB_{str(i-9).zfill(4)}",
            "payment_id": f"PAY_{target['transaction_id'].split('_')[1]}",
            "chargeback_date": (datetime.strptime(target["transaction_date"], "%Y-%m-%d") + timedelta(days=random.randint(15, 30))).strftime("%Y-%m-%d"),
            "amount": target["amount"],
            "reason": random.choice(["fraud", "not_received", "not_as_described", "duplicate"]),
            "status": random.choice(["open", "resolved", "disputed"])
        })

    os.makedirs(os.path.join(output_dir, "synthetic"), exist_ok=True)

    # Save Dev Set (first 80) and Test Set (last 20 for base records)
    def split_and_save(data, name, id_field):
        if not data: return
        df = pd.DataFrame(data)
        # simplistic split based on record index (roughly matches 80/20)
        df_dev = df.iloc[:int(len(df)*0.8)]
        df_test = df.iloc[int(len(df)*0.8):]
        df_dev.to_csv(os.path.join(output_dir, "synthetic", f"{name}_dev.csv"), index=False)
        df_test.to_csv(os.path.join(output_dir, "synthetic", f"{name}_test.csv"), index=False)
        df.to_csv(os.path.join(output_dir, "synthetic", f"{name}.csv"), index=False)

    split_and_save(bank_txs, "bank_transactions", "transaction_id")
    split_and_save(settlements, "razorpay_settlements", "settlement_id")
    split_and_save(ledger, "internal_ledger", "ledger_id")
    split_and_save(refunds, "refunds", "refund_id")
    split_and_save(chargebacks, "chargebacks", "chargeback_id")
    
    with open(os.path.join(output_dir, "synthetic", "ground_truth.json"), "w") as f:
        json.dump(ground_truth, f, indent=4)
        
    print(f"Generated data:")
    print(f"- Bank Transactions: {len(bank_txs)}")
    print(f"- Settlements: {len(settlements)}")
    print(f"- Ledger Records: {len(ledger)}")
    print(f"- Refunds: {len(refunds)}")
    print(f"- Chargebacks: {len(chargebacks)}")

if __name__ == "__main__":
    generate_data()
