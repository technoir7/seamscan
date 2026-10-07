const { exportCsv } = require("../lib/export");

describe("exportCsv", () => {
  it.skip("streams large exports", async () => {
    const rows = Array.from({ length: 100_000 }, (_, i) => ({ id: i }));
    expect((await exportCsv(rows)).split("\n")).toHaveLength(100_001);
  });

  it.only("writes a header row", async () => {
    expect((await exportCsv([{ id: 1 }])).split("\n")[0]).toBe("id");
  });
});
