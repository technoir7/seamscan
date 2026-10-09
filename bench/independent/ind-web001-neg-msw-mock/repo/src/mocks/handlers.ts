import { http, HttpResponse } from "msw";
import { db } from "./fakeDb";

export const handlers = [
  http.post("/api/todos", async ({ request }) => {
    const body = (await request.json()) as { title: string };
    const todo = db.todo.create({ title: body.title });
    return HttpResponse.json(todo, { status: 201 });
  }),
];
