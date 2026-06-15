---
name: Orval Zod codegen collision fix
description: How to prevent TS2308 duplicate export errors when Orval generates both Zod schemas and TypeScript type files
---

## The problem
When an OpenAPI endpoint has a **query parameter** (not just path params), Orval v8 generates:
1. `lib/api-zod/src/generated/api.ts` — `export const XxxParams = zod.object({...})`
2. `lib/api-zod/src/generated/types/xxxParams.ts` — `export type XxxParams = {...}`

Both barrel-exported from `lib/api-zod/src/index.ts` → TS2308 ambiguity error.

**Why:** The `schemas: { path: "generated/types", type: "typescript" }` key in the Orval zod output config tells Orval to generate separate TypeScript type files for all schemas including query-param types. Those names collide with the Zod schema values of the same name.

## The fix
Remove `schemas` from the Orval zod output config in `lib/api-spec/orval.config.ts`:

```ts
// Remove this line:
schemas: { path: "generated/types", type: "typescript" },
```

Update `lib/api-zod/src/index.ts` to only export from the generated api file:

```ts
export * from "./generated/api";
```

**How to apply:** Any time a new endpoint with query parameters is added to the OpenAPI spec, run codegen and check for TS2308. If hit, the schemas config is the culprit.

Note: `export type *` does NOT resolve this ambiguity — TypeScript still flags it even when one side is type-only.
