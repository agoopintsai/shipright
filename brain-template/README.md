# Brain

This repo is the project's memory: decisions with their WHY, current direction, and an append-only progress log. Humans sign what goes in; tools only lint it.

## How to read it

1. `INDEX.md` lists the products.
2. `products/<product>/DIRECTION.md` says where that product is heading now and which decisions are active.
3. `products/<product>/MAP.md` says what lives where.
4. `products/<product>/decisions/` and `shared/decisions/` hold the decision docs, one file per decision.

Read DIRECTION before starting any work on a product. The rules for writing are in `GOVERNANCE.md`.

## Layout

```
INDEX.md  GOVERNANCE.md
products/<product>/{DIRECTION.md,MAP.md,decisions/,log.md}
shared/decisions/      decisions that affect more than one product
inbox/                 unsorted quick notes
templates/             decision, consensus and spec templates
```
