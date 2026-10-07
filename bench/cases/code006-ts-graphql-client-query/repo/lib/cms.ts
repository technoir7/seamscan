import { GraphQLClient } from "./graphql-client";

const client = new GraphQLClient(process.env.CMS_URL!, process.env.CMS_TOKEN!);

export async function getPage(slug: string) {
  const data = await client.query(`
    query {
      page(where: { slug: "${slug}" }) {
        title
        body { html }
      }
    }
  `);
  return data.page;
}
