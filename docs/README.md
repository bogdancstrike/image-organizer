# Auto Image Organizer: documentation

| Doc | What's inside |
|---|---|
| [Getting started](getting-started.md) | Install, first sort, choosing a folder, apply & undo |
| [Configuration](configuration.md) | Environment variables, volumes, AI settings |
| [Organizing modes & categories](categories.md) | Presets, custom categories, auto-discovery, by date, AI assist |
| [Architecture](architecture.md) | How the pipeline, the API and the animation fit together |
| [API reference](api.md) | REST + Server-Sent Events endpoints |
| [Development](development.md) | Local dev loop, tests, end-to-end check, project layout |

## Specifications
Specs follow the [OpenSpec](https://github.com/Fission-AI/OpenSpec) style: requirements with IDs and WHEN/THEN scenarios.

- [Project](openspec/project.md): purpose, principles, stack, glossary
- Capability specs: [library-scanning](openspec/specs/library-scanning/spec.md) ·
  [media-analysis](openspec/specs/media-analysis/spec.md) · [categorization](openspec/specs/categorization/spec.md) ·
  [duplicate-detection](openspec/specs/duplicate-detection/spec.md) · [organize-apply-undo](openspec/specs/organize-apply-undo/spec.md) ·
  [web-ui](openspec/specs/web-ui/spec.md) · [deployment](openspec/specs/deployment/spec.md)
- [Implementation plan](implementation-plan.md) · [Tasks](tasks.md) · [Acceptance criteria](acceptance-criteria.md)
