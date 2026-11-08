from __future__ import annotations

import re
from typing import Dict, Optional, Tuple


class SkillNormalizationService:
    """
    Controlled skill normalization system.
    Maps known synonyms and aliases to canonical skill tokens while strictly
    guaranteeing that distinct technologies remain distinct:
      - 'Spring' != 'Spring Boot'
      - 'Java' != 'JavaScript'
      - 'C' != 'C++' != 'C#'
      - 'AngularJS' != 'Angular'
    """

    # Controlled canonical alias dictionary (lowercased key -> canonical identifier)
    CANONICAL_ALIASES: Dict[str, str] = {
        # Java & JVM
        "java": "java",
        "core java": "java",
        "java 8": "java",
        "java 11": "java",
        "java 17": "java",
        "java 21": "java",
        "spring boot": "spring_boot",
        "springboot": "spring_boot",
        "spring-boot": "spring_boot",
        "spring": "spring_framework",
        "spring framework": "spring_framework",
        "spring mvc": "spring_mvc",
        "hibernate": "hibernate",
        "jpa": "jpa",
        "kotlin": "kotlin",
        "scala": "scala",

        # JavaScript / TypeScript Ecosystem
        "javascript": "javascript",
        "js": "javascript",
        "ecmascript": "javascript",
        "typescript": "typescript",
        "ts": "typescript",
        "react": "react",
        "react.js": "react",
        "reactjs": "react",
        "react native": "react_native",
        "node": "nodejs",
        "node.js": "nodejs",
        "nodejs": "nodejs",
        "express": "expressjs",
        "express.js": "expressjs",
        "expressjs": "expressjs",
        "next.js": "nextjs",
        "nextjs": "nextjs",
        "vue": "vue",
        "vue.js": "vue",
        "vuejs": "vue",
        "angular": "angular",
        "angular 2+": "angular",
        "angularjs": "angularjs",
        "angular.js": "angularjs",

        # Systems & Compiled Languages
        "c": "c_lang",
        "c++": "cpp",
        "cpp": "cpp",
        "c#": "csharp",
        "csharp": "csharp",
        ".net": "dotnet",
        "dotnet": "dotnet",
        ".net core": "dotnet_core",
        "dotnet core": "dotnet_core",
        "go": "golang",
        "golang": "golang",
        "rust": "rust",

        # Python & AI
        "python": "python",
        "python 3": "python",
        "fastapi": "fastapi",
        "django": "django",
        "flask": "flask",
        "pandas": "pandas",
        "numpy": "numpy",
        "pytorch": "pytorch",
        "tensorflow": "tensorflow",

        # Cloud & DevOps
        "aws": "aws",
        "amazon web services": "aws",
        "gcp": "gcp",
        "google cloud": "gcp",
        "google cloud platform": "gcp",
        "azure": "azure",
        "microsoft azure": "azure",
        "docker": "docker",
        "kubernetes": "kubernetes",
        "k8s": "kubernetes",
        "terraform": "terraform",
        "ansible": "ansible",
        "ci/cd": "cicd",
        "cicd": "cicd",
        "jenkins": "jenkins",
        "github actions": "github_actions",

        # Databases & Streaming
        "postgresql": "postgresql",
        "postgres": "postgresql",
        "mysql": "mysql",
        "mongodb": "mongodb",
        "redis": "redis",
        "kafka": "apache_kafka",
        "apache kafka": "apache_kafka",
        "rabbitmq": "rabbitmq",
        "elasticsearch": "elasticsearch",

        # Architecture & Protocols
        "microservices": "microservices",
        "micro services": "microservices",
        "micro-services": "microservices",
        "rest": "rest_api",
        "restful": "rest_api",
        "rest api": "rest_api",
        "restful apis": "rest_api",
        "rest apis": "rest_api",
        "graphql": "graphql",
        "grpc": "grpc",
    }

    def normalize(self, raw_skill: str) -> str:
        """
        Normalize a raw skill string into its canonical identifier.
        Preserves original capitalization separately.
        """
        if not raw_skill:
            return ""

        cleaned = raw_skill.strip().lower()
        cleaned = re.sub(r"\s+", " ", cleaned)

        # 1. Exact alias match
        if cleaned in self.CANONICAL_ALIASES:
            return self.CANONICAL_ALIASES[cleaned]

        # 2. Controlled suffix cleanup (e.g., 'developer', 'programming')
        stripped = re.sub(r"\b(developer|development|programming|engineer|engineering)\b", "", cleaned).strip()
        stripped = re.sub(r"\s+", " ", stripped)
        if stripped in self.CANONICAL_ALIASES:
            return self.CANONICAL_ALIASES[stripped]

        # 3. Fallback: slugify standard tokens
        slug = re.sub(r"[^a-z0-9+#.]+", "_", cleaned).strip("_")
        return slug

    def is_match(self, skill_a: str, skill_b: str) -> bool:
        """
        Returns True if skill_a and skill_b resolve to the exact same canonical skill.
        Strictly prevents unauthorized cross-skill matching (e.g., Java != JavaScript,
        Spring != Spring Boot).
        """
        norm_a = self.normalize(skill_a)
        norm_b = self.normalize(skill_b)

        if not norm_a or not norm_b:
            return False

        return norm_a == norm_b


skill_normalizer = SkillNormalizationService()
