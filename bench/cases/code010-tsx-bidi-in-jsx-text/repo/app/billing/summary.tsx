export default function Summary({ total }: { total: number }) {
  return (
    <section>
      <h2>Order summary</h2>
      <p>Refund due: ‮00.001$‬</p>
      <p>Total: ${total.toFixed(2)}</p>
    </section>
  );
}
