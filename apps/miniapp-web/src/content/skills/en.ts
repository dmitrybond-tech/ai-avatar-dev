import type { SkillTile } from './types'

export const skills: SkillTile[] = [
  {
    key: 'automation',
    title: 'Automation & ETL/ELT (Python)',
    short: 'Pandas, data migrations, cron-safe jobs',
    details:
      'Designs and ships pragmatic data automation: ingestion jobs, CSV/JSON transforms, CRM ↔ analytics bridges, and Notion/Sheets synchronisation. Builds Python services with structured logging, retries, and idempotent runs so cron tasks stay reliable.',
    tags: ['Python', 'ETL', 'Automation'],
  },
  {
    key: 'cloud',
    title: 'Cloud Architecture',
    short: 'AWS · Azure · GCP',
    details:
      'Plans migrations and hybrid setups, keeps Terraform/ARM/CDK tidy, and focuses on cost visibility. Helps teams move from “pet servers” to predictable infra with least-privilege access, backups, and monitoring in place.',
    tags: ['Terraform', 'AWS', 'Azure', 'GCP'],
  },
  {
    key: 'integrations',
    title: 'Integrations & APIs',
    short: 'REST, webhooks, gRPC, queue-driven flows',
    details:
      'Designs integration contracts, handles auth variants (API keys, OAuth, JWT), and makes webhooks reliable with retries, signature checks, and observability. Bridges product gaps by stitching together SaaS, internal tooling, and legacy APIs.',
    tags: ['APIs', 'Webhooks', 'OAuth'],
  },
  {
    key: 'devops',
    title: 'CI/CD & Delivery',
    short: 'Containers, Actions, Compose',
    details:
      'Sets up build pipelines, preview environments, and promotion flows with guardrails. Works with Docker, GitHub Actions, and lightweight GitOps so releases stay boring. Coaches teams on branching, reviews, and release checklists.',
    tags: ['CI/CD', 'Docker', 'GitHub Actions'],
  },
  {
    key: 'product',
    title: 'Product & Delivery',
    short: 'Discovery → launch → feedback loops',
    details:
      'Keeps delivery grounded in outcomes: clarifies problem statements, runs discovery spikes, and writes concise acceptance criteria. Partners with founders/PMs on shaping increments that can ship in days, not months.',
    tags: ['Product', 'Delivery'],
  },
  {
    key: 'appsec',
    title: 'Application Security Basics',
    short: 'Secure defaults, SDLC hygiene',
    details:
      'Bakes in practical security: secret management, dependency scanning, basic SAST/SCA, and threat-model-lite reviews. Helps teams adopt least privilege, rotate tokens, and document “secure by default” configs.',
    tags: ['Security', 'AppSec'],
  },
  {
    key: 'data',
    title: 'Data & Analytics Enablement',
    short: 'Dashboards, product metrics, insight loops',
    details:
      'Bootstraps foundational analytics: tracking plans, event schemas, and dashboards that answer real questions. Aligns product and growth teams around metrics, cohort analysis, and experiments rooted in measurable signals.',
    tags: ['Analytics', 'Metrics'],
  },
  {
    key: 'webdev',
    title: 'Web & App Development',
    short: 'React, Vite, FastAPI, TypeScript',
    details:
      'Delivers cohesive slices across frontend and backend: shared API contracts, typed clients, and performance-aware UX. Prefers DX-friendly tooling so teams can iterate quickly without accumulating fragile hacks.',
    tags: ['React', 'TypeScript', 'FastAPI'],
  },
]


