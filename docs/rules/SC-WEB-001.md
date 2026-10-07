# SC-WEB-001 — Server write without an auth check

**Severity:** HIGH · **Confidence:** MEDIUM · **CWE:** [CWE-862](https://cwe.mitre.org/data/definitions/862.html) · **Languages:** Python, TypeScript/JavaScript

## What it finds

A server handler that accepts a mutating request and writes data before any check of
who is calling. The finding points at the first write; its related location is the
handler.

**Handlers in scope**

| Framework | Handler |
|---|---|
| Next.js app router | `app/**/route.{ts,js}` exporting `POST`, `PUT`, `PATCH` or `DELETE` (a function, a `const`, `export { fn as POST }`, or a function passed to a wrapper) |
| Next.js server actions | every exported function of a `"use server"` file, and any function whose body starts with `"use server"` |
| Next.js pages router | the default export of `pages/api/**` (it accepts every method unless it checks `req.method`) |
| Express, Hono, Fastify | `x.post/put/patch/delete("/path", ...middleware, handler)`, where the handler is a function, a function in the same file, or a function passed to a wrapper such as `asyncHandler(...)` |
| FastAPI, Flask | functions decorated `@x.post/put/patch/delete(...)`, or `@x.route(...)` / `@x.api_route(...)` with a mutating method in `methods=` |
| Django, DRF | function views with `@require_POST`, `@require_http_methods([...])` or `@api_view([...])` naming a mutating method, or whose `request` parameter is compared to `"POST"` etc.; `post/put/patch/delete` methods of classes deriving from `*View`, `*APIView`, `*ViewSet`, `MethodView`, `Resource` or `HTTPEndpoint` |

**Writes**

| Library | Calls |
|---|---|
| Supabase | `.from(t).insert/update/upsert/delete(...)`, Python `.table(t)` / `.from_(t)` likewise |
| Prisma | `<db>.<model>.create/createMany/createManyAndReturn/update/updateMany/upsert/delete/deleteMany`, where `<db>` is `prisma`, `db`, `tx`, `trx` or `database` |
| Drizzle | `db.insert/update/delete(table)` on the same receivers |
| MongoDB, Mongoose | `insertOne/Many`, `updateOne/Many`, `deleteOne/Many`, `replaceOne`, `bulkWrite`, `findOneAnd*`, `findByIdAnd*` on any receiver; `Model.create/update/upsert/destroy/bulkCreate(doc)` on a capitalised model; `.save()` on a document made with `new Model(...)` or loaded with `Model.find*(...)` |
| SQLAlchemy | `add/add_all/merge/delete/bulk_save_objects` on a session-like receiver (`db`, `session`, `db.session`, `*session`), `execute(insert/update/delete(...))`, `execute("UPDATE ...")` / `text(...)`, and a bare `commit()` when the handler has no other recognised write (it saves attribute changes) |
| Django ORM | `Model.objects.create/get_or_create/update_or_create/bulk_create/bulk_update`, `.update()` / `.delete()` on a queryset (`.objects`, `.filter`, `.exclude`, `.query`), `obj.delete()`, `.save()` (not `save(commit=False)`) |
| PyMongo | `insert_one/many`, `update_one/many`, `delete_one/many`, `replace_one`, `bulk_write`, `find_one_and_*` |

**Auth checks.** Any of these, earlier in the handler than the first write (or inside
the write's own arguments, which run first), means no finding:

- A call whose last name segment, lowercased without underscores, is a known primitive:
  `auth()`, `getServerSession`, `getSession`, `getUser` (`supabase.auth.getUser`),
  `getClaims`, `currentUser`, `getCurrentUser`, `getToken`, `getAuth`, `protect`
  (`auth.protect()`), `verify` (svix webhooks), `verifySession`, `validateRequest`,
  `getKindeServerSession`, `jwtVerify`, `verifyToken`, `verifyIdToken`,
  `verifyAccessToken`, `get_jwt_identity`, `verify_jwt_in_request`, `timingSafeEqual`,
  `compare_digest`, `jsonwebtoken.verify`, `jwt.decode`; or one starting with
  `requireUser`, `requireAuth`, `requireSession`, `requireLogin`, `requireAdmin`,
  `requireRole`, `ensureAuth`, `ensureUser`, `isAuthenticated`, `checkAuth`,
  `assertAuth`, `authenticate`, `withAuth`, `constructEvent` (Stripe), `verifyWebhook`,
  `verifySignature`.
- A request turned away with 401 or 403: `{ status: 401 }`, `res.status(403)`,
  `c.json(..., 401)`, `abort(403)`, `HTTPException(status_code=401)`,
  `status.HTTP_401_UNAUTHORIZED`, or raising `PermissionDenied` / `NotAuthenticated` /
  `*Unauthorized*` / `*Forbidden*`. Some check must have come first. This covers cron
  routes that compare a bearer token to `process.env.CRON_SECRET`.
- Python: `request.user`, `self.request.user` or Flask-Login's `current_user` used
  before the write, and any `.is_authenticated` check. A write scoped to the logged-in
  user fails for an anonymous caller (the ORM rejects `AnonymousUser`) rather than
  succeeding.
- Express/Hono/Fastify middleware in the registration (`app.post("/x", requireAuth,
  handler)`), Fastify `preHandler`/`onRequest`/`preValidation` options, or an earlier
  `x.use(...)` / `x.addHook(...)` on the same object with auth-like middleware. A path
  passed to `use` (`app.use("/api/*", jwt(...))`) must prefix the route. Names count when
  they mention `auth`, `login`, `jwt`, `protect`, `token`, `guard`, `signedin`, `verify`.
  Routers (`authRoutes`, `authRouter`) and CSRF middleware don't count.
- An auth-named wrapper around the handler: `export const POST = withAuth(...)`.
- Decorators: `@login_required`, `@permission_required`, `@jwt_required`, anything
  mentioning `login`, `auth`, `permission`, `jwt`, `token`, `role`, `staff`, `admin`,
  `superuser`; `method_decorator(login_required, ...)` on a class; DRF
  `permission_classes` other than only `AllowAny`, or the project's
  `REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]` when the view sets none.
- FastAPI: a parameter `Depends(...)` / `Security(...)` whose target mentions `user`,
  `auth`, `login`, `token`, `admin`, `permission`, `apikey`, `principal`, `verify`,
  `signature` or `current`; an `Annotated[..., Depends(...)]` annotation, including an
  alias like `CurrentUser` defined in another module; `dependencies=[...]` on the route
  or on its `APIRouter(...)`. `Depends(get_db)` is a database session, not a check.
- Django class bases such as `LoginRequiredMixin`, `PermissionRequiredMixin`,
  `UserPassesTestMixin`; Flask `@bp.before_request` hooks that check the user (they
  cover every route on that blueprint in the same file).
- Next.js `middleware.ts` (or `src/middleware.ts`) that checks auth (an auth call or a
  401/403, or `export { default } from "next-auth/middleware"`) and whose
  `config.matcher` lists plain path patterns (`/admin/:path*`, `/api/admin/:path+`,
  `/settings`) covering the route's URL. Route groups `(group)` and `@slots` are
  ignored when working out the URL.

**Deliberately public writes (not flagged)**

- Analytics, logging and audit tables: the table or model name contains the word
  `analytics`, `telemetry`, `log(s)`, `audit`, `pageview(s)`, `metrics` or
  `impressions` (`analytics_events`, `PageView`, `audit_logs`). Public beacons write
  these on purpose.
- Sign-up, login and password-reset flows: the route path, route file or function name
  contains the word `register`, `registration`, `signup`, `login`, `signin`, `logout`,
  `signout`, `forgot-password`, `reset-password`, `verify-email`, `callback` or `oauth`,
  unless it also contains `admin` (`/admin/users/{id}/reset-password` is flagged).
- Webhooks that verify a signature first (`stripe.webhooks.constructEvent`, svix
  `wh.verify`): the verification is the auth check.

GET handlers are out of scope. A view counter incremented in a GET is not reported.

Test files are skipped, and so are MSW request mocks (files importing `msw`).

## Why it matters

A route that writes without checking the caller lets anyone change or delete data:
other users' profiles, orders, posts. AI assistants often generate the handler and the
query correctly and leave out the one line that asks who is calling. Or they add it
after the write, or rely on a middleware whose matcher doesn't cover the new route.

## Examples

Flagged:

```ts
// app/api/posts/route.ts
export async function POST(req: Request) {
  const body = PostSchema.parse(await req.json());
  const post = await prisma.post.create({ data: body });       // no session check
  return NextResponse.json(post, { status: 201 });
}

router.delete("/:id", async (req, res) => {                     // GET and PUT have requireAuth
  await User.findByIdAndDelete(req.params.id);
  res.status(204).end();
});

export async function PATCH(req: Request, { params }) {
  const project = await prisma.project.update({ where: { id }, data });  // auth() comes later
  const session = await auth();
}
```

```python
@router.post("/", status_code=201)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    db.add(models.Item(**item.model_dump()))        # Depends(get_db) is not auth
    db.commit()

def edit_profile(request, username):                 # no @login_required
    profile = get_object_or_404(Profile, user__username=username)
    if request.method == "POST":
        profile.bio = request.POST.get("bio", "")
        profile.save()
```

Not flagged:

```ts
export async function POST(req: Request) {
  const session = await getServerSession(authOptions);
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  await prisma.bookmark.create({ data: { ... } });
}

router.post("/", writeLimiter, requireAuth, async (req, res) => { await Note.create(...) });

event = stripe.webhooks.constructEvent(body, signature, secret);    // then upsert
await supabase.from("analytics_events").insert({ path });           // public beacon
```

```python
def create_note(note: NoteCreate, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)): ...
class BookmarkView(LoginRequiredMixin, View): ...
```

## How to fix

Check the caller before the first write: `auth()`, `getServerSession`,
`supabase.auth.getUser()`, `Depends(get_current_user)`, `@login_required`. Then scope the
write to that user (`where: { id, userId: session.user.id }`). If middleware protects
the route, make sure its matcher covers the route's path. If the route really is
public (a contact form, a waitlist), suppress the finding with a reason on the write's
line: `// seamscan: ignore[SC-WEB-001] reason: public waitlist signup`.

## Known gaps

False positives:

- **Auth applied elsewhere.** Middleware mounted in another file
  (`app.use("/api", requireAuth, notesRouter)` in `server.js`), FastAPI
  `include_router(router, dependencies=[...])`, `login_required(view)` wrapped in
  `urls.py`, and Next.js middleware whose `matcher` is a regex (Clerk's and Supabase's
  default `"/((?!_next|...).*)"`) aren't seen. Such routes are reported.
- **Public forms.** Contact forms, waitlists and newsletter sign-ups that write to a
  table are reported; suppress them with a reason.
- **Supabase RLS.** A write through the user's own Supabase client (cookie session) is
  also guarded by row-level security when the table has policies. This rule doesn't
  read migrations, so it still asks for an explicit `getUser()`.

False negatives:

- **Intra-procedural.** A write inside a helper (`await createPost(data)`,
  a repository function, a controller imported from another file:
  `router.post("/", createGoal)`) is not seen, and the handler isn't reported.
- **Any check counts.** A call named like an auth primitive is trusted, even an
  unrelated `db.getUser(id)`. So is any 401/403 before the write, and any auth-named
  middleware or decorator.
- Order is source order. A check in an `if` branch that doesn't cover the write still
  counts.
- A Django function view that never compares `request.method` and has no method
  decorator is out of scope, even when it writes.
- Supabase Edge Functions (`Deno.serve`), tRPC procedures, GraphQL resolvers and DRF
  `ModelViewSet`s (which write inside the framework) are not handlers here.
- Writes through other clients (Kysely, Knex without `.from`, raw `pg`
  `client.query("INSERT ...")`, Firebase) aren't recognised.
- The public-flow word list exempts any route whose path or name contains those words
  (`/api/oauth/tokens` that writes something unrelated).

## References

- CWE-862: Missing Authorization
- OWASP API Security Top 10 2023, API1 (Broken Object Level Authorization) and API5
  (Broken Function Level Authorization)
- Next.js documentation, "Authentication: Authorizing Server Actions and Route Handlers"
