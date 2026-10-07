const request = require("supertest");
const chai = require("chai");
const app = require("../server/app");

chai.should();

describe("GET /api/products", () => {
  it("responds with json", () => {
    return request(app)
      .get("/api/products")
      .set("Accept", "application/json")
      .expect("Content-Type", /json/)
      .expect(200);
  });

  it("returns an id for every product", async () => {
    const res = await request(app).get("/api/products");
    res.body.forEach((product) => product.should.have.property("id"));
  });

  it("returns 404 for an unknown product", async () => {
    const res = await request(app).get("/api/products/999999");
    chai.expect(res.status).to.equal(404);
  });
});
