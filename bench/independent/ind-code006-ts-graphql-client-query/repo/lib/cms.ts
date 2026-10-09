import { cmsClient } from "./cmsClient";

export async function getPage(slug: string) {
  const res = await cmsClient.query(`query { page(where: { slug: "${slug}" }) { title body } }`);
  return res.data.page;
}
