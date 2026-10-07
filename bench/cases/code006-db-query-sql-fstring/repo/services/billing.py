import records

db = records.Database("postgresql://localhost/billing")


def invoices_for(customer_id):
    return db.query(f"SELECT * FROM invoices WHERE customer_id = {customer_id}").all()
