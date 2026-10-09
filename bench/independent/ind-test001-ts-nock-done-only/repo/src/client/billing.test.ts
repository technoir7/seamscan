import nock from "nock";
import { fetchInvoices } from "./billing";

it("requests invoices with the api key header", async () => {
  const scope = nock("https://api.billing.example", { reqheaders: { "x-api-key": "k" } })
    .get("/v1/invoices")
    .reply(200, []);
  await fetchInvoices("k");
  scope.done();
});
