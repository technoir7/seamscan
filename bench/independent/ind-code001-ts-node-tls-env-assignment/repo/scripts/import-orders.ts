process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

async function main() {
  const res = await fetch("https://erp.internal.example/orders.json");
  const orders = await res.json();
  console.log(`fetched ${orders.length} orders`);
}

main();
