"""Fallback skills provider with hardcoded minimal skillset."""
from __future__ import annotations

from typing import List

from .skills_loader import SkillRecord


def get_fallback_skills() -> List[SkillRecord]:
    """Return minimal hardcoded skillset as fallback when CSV cannot be loaded."""
    return [
        SkillRecord(
            key="automation",
            title_en="Automation",
            title_ru="Автоматизация",
            short_en="Python ETL/ELT, migrations, and glue between your systems.",
            short_ru="Python ETL/ELT, миграции и связка ваших систем.",
            tags=["python", "etl", "elt", "migrations", "integrations"],
            bullets_en=[
                "Build ETL/ELT pipelines in Python (pandas, SQLAlchemy; cron or lightweight schedulers).",
                "Write data and infrastructure migration scripts (DBs, cloud moves to AWS/Azure/GCP).",
                "Automate routine tasks and back-office workflows.",
            ],
            bullets_ru=[
                "Проектирование ETL/ELT-пайплайнов на Python (pandas, SQLAlchemy; cron или лёгкие планировщики).",
                "Скрипты миграций данных и инфраструктуры (БД, переносы в AWS/Azure/GCP).",
                "Автоматизация рутины и бэк-офисных процессов.",
            ],
            examples_en=["Clean CSV → PostgreSQL nightly", "Migrate MySQL → Aurora"],
            examples_ru=["Ночной импорт CSV → PostgreSQL", "Миграция MySQL → Aurora"],
            weight=0,
            pinned=False,
        ),
        SkillRecord(
            key="cloud-devops",
            title_en="Cloud & DevOps",
            title_ru="Облако и DevOps",
            short_en="AWS/Azure/GCP, IaC, CI/CD, containers.",
            short_ru="AWS/Azure/GCP, IaC, CI/CD, контейнеры.",
            tags=["cloud", "aws", "azure", "gcp", "iac", "cicd"],
            bullets_en=[
                "Design secure cloud architectures and landing zones.",
                "Set up CI/CD pipelines and automated testing.",
                "Containerize services and optimize images.",
            ],
            bullets_ru=[
                "Проектирование безопасных облачных архитектур и landing zone.",
                "Настройка CI/CD и автоматического тестирования.",
                "Контейнеризация сервисов и оптимизация образов.",
            ],
            examples_en=["ECS blue/green deploy", "GH Actions monorepo CI"],
            examples_ru=["Blue/green деплой на ECS", "GH Actions CI для монорепы"],
            weight=0,
            pinned=False,
        ),
    ]

