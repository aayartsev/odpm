# Which docs to read

The site hosts several **documentation versions**. Use the version selector in the header. Quick guide:

| Version | Audience | odpm install |
|---------|----------|--------------|
| **stable** (recommended) | production, new users | APT `stable` suite, [stable GitHub Release](https://github.com/aayartsev/odpm/releases) |
| **4.3** / **4.3.0** | staying on 4.3.x | 4.3.0 `.deb` / `.rpm` from Releases |
| **4.4.2-beta** and other `*-beta` | early 4.4 adopters | APT `testing` suite, [beta release](https://github.com/aayartsev/odpm/releases) |
| **dev** | odpm development, `4.4-dev` HEAD | not for production end users |

## Quick links

- Stable install hub: `/stable/install/` on this site
- 4.3 archive: `/4.3.0/install/` (alias **4.3** in the selector)
- 4.4 beta: `/4.4.2-beta/install/`
- Development docs: `/dev/install/`

!!! tip "odpm version ≠ docs version"
    `odpm --version` is the **installed manager**. Site docs are versioned **separately** by release tags and the `stable` alias.

## Next

- [Installing odpm](../install/README.md)
- [Local dev from scratch](local-dev-from-scratch.md)
