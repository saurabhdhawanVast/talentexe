"""
Management command: seed_employees

Creates 6 dummy employee accounts (Supabase Auth + DB records) with full
profile data — skills, experience, projects, education, certifications, and
languages.

  3 employees  →  profile_status = 'submitted'  (+ pending ProfileReview)
  3 employees  →  profile_status = 'incomplete'

Usage:
    python manage.py seed_employees
    python manage.py seed_employees --clear   # delete existing seed users first
"""
from __future__ import annotations

import datetime
import uuid

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.users.services import create_supabase_user, get_supabase_admin_client

SEED_PASSWORD = "Demo@12345"

# ---------------------------------------------------------------------------
# Employee data
# ---------------------------------------------------------------------------

EMPLOYEES = [
    # ── submitted ─────────────────────────────────────────────────────────
    {
        "email": "priya.sharma@talentexe.demo",
        "full_name": "Priya Sharma",
        "designation": "Senior Frontend Developer",
        "department": "Engineering",
        "location": "Bengaluru, India",
        "experience_years": 5.0,
        "profile_status": "submitted",
        "summary": (
            "Passionate frontend engineer with 5 years of experience building "
            "high-performance web applications using React and TypeScript. "
            "Strong eye for UI/UX and a track record of delivering delightful "
            "user experiences at scale."
        ),
        "languages": [
            {"name": "English", "proficiency": "Fluent"},
            {"name": "Hindi", "proficiency": "Native"},
            {"name": "Kannada", "proficiency": "Conversational"},
        ],
        "linkedin_url": "https://linkedin.com/in/priya-sharma-demo",
        "github_url": "https://github.com/priya-sharma-demo",
        "portfolio_url": "https://priyasharma.dev",
        "skills": [
            {"name": "React", "category": "Frontend", "level": "Expert", "years": 5.0, "primary": True},
            {"name": "TypeScript", "category": "Language", "level": "Expert", "years": 4.0, "primary": True},
            {"name": "Next.js", "category": "Frontend", "level": "Expert", "years": 3.0, "primary": False},
            {"name": "Tailwind CSS", "category": "Frontend", "level": "Intermediate", "years": 2.0, "primary": False},
            {"name": "GraphQL", "category": "API", "level": "Intermediate", "years": 2.0, "primary": False},
        ],
        "experience": [
            {
                "company_name": "Razorpay",
                "designation": "Senior Frontend Developer",
                "employment_type": "Full-Time",
                "start_date": datetime.date(2022, 3, 1),
                "end_date": None,
                "is_current": True,
                "location": "Bengaluru, India",
                "description": (
                    "Led frontend architecture for the merchant dashboard serving 500K+ businesses. "
                    "Reduced bundle size by 40% through code-splitting and lazy loading strategies."
                ),
            },
            {
                "company_name": "Freshworks",
                "designation": "Frontend Developer",
                "employment_type": "Full-Time",
                "start_date": datetime.date(2019, 6, 1),
                "end_date": datetime.date(2022, 2, 28),
                "is_current": False,
                "location": "Chennai, India",
                "description": (
                    "Built and maintained the CRM product UI using React. "
                    "Introduced Storybook-driven component library adopted by 3 product teams."
                ),
            },
        ],
        "projects": [
            {
                "name": "Merchant Analytics Dashboard",
                "client_name": "Razorpay",
                "description": (
                    "Real-time analytics dashboard for merchants to track payments, refunds, and settlements. "
                    "Built with React, TypeScript, and Recharts. Handles 1M+ data points with virtualized tables."
                ),
                "role": "Tech Lead",
                "team_size": 6,
                "start_date": datetime.date(2022, 9, 1),
                "end_date": datetime.date(2023, 4, 30),
                "is_current": False,
                "skills": ["React", "TypeScript", "GraphQL"],
            },
            {
                "name": "Design System – Emerald UI",
                "client_name": "Freshworks",
                "description": (
                    "Shared component library (60+ components) built with React and Storybook, "
                    "used across 5 product suites. Reduced design inconsistency by 70%."
                ),
                "role": "Frontend Engineer",
                "team_size": 4,
                "start_date": datetime.date(2021, 1, 1),
                "end_date": datetime.date(2021, 12, 31),
                "is_current": False,
                "skills": ["React", "TypeScript", "Tailwind CSS"],
            },
        ],
        "education": [
            {
                "degree": "B.Tech in Computer Science",
                "institution": "National Institute of Technology, Trichy",
                "start_year": 2015,
                "end_year": 2019,
                "grade": "8.7 CGPA",
            }
        ],
        "certifications": [
            {
                "name": "AWS Certified Developer – Associate",
                "issuer": "Amazon Web Services",
                "issue_date": datetime.date(2023, 1, 15),
                "expiry_date": datetime.date(2026, 1, 15),
                "credential_url": "https://aws.amazon.com/certification/",
            },
            {
                "name": "Meta Frontend Developer Professional Certificate",
                "issuer": "Meta / Coursera",
                "issue_date": datetime.date(2021, 8, 10),
                "expiry_date": None,
                "credential_url": "https://coursera.org/professional-certificates/meta-front-end-developer",
            },
        ],
    },
    {
        "email": "rahul.mehta@talentexe.demo",
        "full_name": "Rahul Mehta",
        "designation": "Backend Engineer",
        "department": "Engineering",
        "location": "Mumbai, India",
        "experience_years": 4.0,
        "profile_status": "submitted",
        "summary": (
            "Backend engineer specialising in Python/Django and microservices architecture. "
            "Experienced in building high-throughput REST APIs and event-driven systems "
            "using Kafka and Celery. Enjoys solving complex distributed-systems problems."
        ),
        "languages": [
            {"name": "English", "proficiency": "Fluent"},
            {"name": "Hindi", "proficiency": "Native"},
            {"name": "Gujarati", "proficiency": "Native"},
        ],
        "linkedin_url": "https://linkedin.com/in/rahul-mehta-demo",
        "github_url": "https://github.com/rahul-mehta-demo",
        "portfolio_url": "",
        "skills": [
            {"name": "Python", "category": "Language", "level": "Expert", "years": 4.0, "primary": True},
            {"name": "Django", "category": "Backend", "level": "Expert", "years": 4.0, "primary": True},
            {"name": "PostgreSQL", "category": "Database", "level": "Expert", "years": 3.0, "primary": False},
            {"name": "Redis", "category": "Infrastructure", "level": "Intermediate", "years": 2.0, "primary": False},
            {"name": "Docker", "category": "DevOps", "level": "Intermediate", "years": 2.0, "primary": False},
        ],
        "experience": [
            {
                "company_name": "Zepto",
                "designation": "Backend Engineer",
                "employment_type": "Full-Time",
                "start_date": datetime.date(2023, 1, 16),
                "end_date": None,
                "is_current": True,
                "location": "Mumbai, India",
                "description": (
                    "Owns the order management microservice processing 200K+ orders/day. "
                    "Reduced p99 latency from 800ms to 120ms via query optimisation and caching."
                ),
            },
            {
                "company_name": "Meesho",
                "designation": "Software Engineer – Backend",
                "employment_type": "Full-Time",
                "start_date": datetime.date(2020, 7, 1),
                "end_date": datetime.date(2023, 1, 10),
                "is_current": False,
                "location": "Bengaluru, India",
                "description": (
                    "Built seller onboarding APIs serving 1M+ resellers. "
                    "Introduced async task queue (Celery + Redis) for heavy report generation jobs."
                ),
            },
        ],
        "projects": [
            {
                "name": "Order Management Service",
                "client_name": "Zepto",
                "description": (
                    "Event-driven microservice handling order lifecycle from placement to delivery. "
                    "Uses Kafka for async communication and Redis for rate limiting."
                ),
                "role": "Backend Engineer",
                "team_size": 5,
                "start_date": datetime.date(2023, 3, 1),
                "end_date": None,
                "is_current": True,
                "skills": ["Python", "Django", "Redis", "PostgreSQL"],
            },
            {
                "name": "Seller Analytics Platform",
                "client_name": "Meesho",
                "description": (
                    "Data pipeline and REST API layer for seller performance reports. "
                    "Processed 50GB+ daily using Celery workers with S3 export."
                ),
                "role": "Software Engineer",
                "team_size": 4,
                "start_date": datetime.date(2021, 6, 1),
                "end_date": datetime.date(2022, 12, 31),
                "is_current": False,
                "skills": ["Python", "Django", "PostgreSQL"],
            },
        ],
        "education": [
            {
                "degree": "B.E. in Information Technology",
                "institution": "VJTI Mumbai",
                "start_year": 2016,
                "end_year": 2020,
                "grade": "8.2 CGPA",
            }
        ],
        "certifications": [
            {
                "name": "Certified Kubernetes Application Developer (CKAD)",
                "issuer": "Cloud Native Computing Foundation",
                "issue_date": datetime.date(2023, 6, 20),
                "expiry_date": datetime.date(2026, 6, 20),
                "credential_url": "https://www.cncf.io/certification/ckad/",
            }
        ],
    },
    {
        "email": "ananya.singh@talentexe.demo",
        "full_name": "Ananya Singh",
        "designation": "Data Scientist",
        "department": "Analytics",
        "location": "Hyderabad, India",
        "experience_years": 3.0,
        "profile_status": "submitted",
        "summary": (
            "Data scientist with expertise in NLP, recommendation systems, and MLOps. "
            "Proficient in Python, scikit-learn, and PyTorch. Passionate about turning "
            "raw data into actionable insights and shipping ML models to production."
        ),
        "languages": [
            {"name": "English", "proficiency": "Fluent"},
            {"name": "Hindi", "proficiency": "Native"},
        ],
        "linkedin_url": "https://linkedin.com/in/ananya-singh-demo",
        "github_url": "https://github.com/ananya-singh-demo",
        "portfolio_url": "https://ananyasingh.ml",
        "skills": [
            {"name": "Python", "category": "Language", "level": "Expert", "years": 3.0, "primary": True},
            {"name": "Machine Learning", "category": "AI/ML", "level": "Expert", "years": 3.0, "primary": True},
            {"name": "PyTorch", "category": "AI/ML", "level": "Intermediate", "years": 2.0, "primary": False},
            {"name": "SQL", "category": "Database", "level": "Intermediate", "years": 3.0, "primary": False},
            {"name": "Apache Spark", "category": "Data Engineering", "level": "Beginner", "years": 1.0, "primary": False},
        ],
        "experience": [
            {
                "company_name": "PhonePe",
                "designation": "Data Scientist",
                "employment_type": "Full-Time",
                "start_date": datetime.date(2022, 8, 1),
                "end_date": None,
                "is_current": True,
                "location": "Hyderabad, India",
                "description": (
                    "Developed fraud detection ML model reducing false positives by 35%. "
                    "Built NLP pipeline for user intent classification serving 10M+ queries/month."
                ),
            },
            {
                "company_name": "Mu Sigma",
                "designation": "Junior Data Analyst",
                "employment_type": "Full-Time",
                "start_date": datetime.date(2021, 7, 1),
                "end_date": datetime.date(2022, 7, 31),
                "is_current": False,
                "location": "Bengaluru, India",
                "description": (
                    "Delivered business intelligence dashboards for retail client using SQL and Tableau. "
                    "Automated weekly reports saving 12 hours/week for the analytics team."
                ),
            },
        ],
        "projects": [
            {
                "name": "Fraud Detection System",
                "client_name": "PhonePe",
                "description": (
                    "Real-time fraud scoring pipeline using XGBoost and feature store. "
                    "Integrated with payment processing to flag suspicious transactions in <50ms."
                ),
                "role": "Data Scientist",
                "team_size": 5,
                "start_date": datetime.date(2022, 10, 1),
                "end_date": datetime.date(2023, 5, 31),
                "is_current": False,
                "skills": ["Python", "Machine Learning", "SQL"],
            },
            {
                "name": "User Intent NLP Classifier",
                "client_name": "PhonePe",
                "description": (
                    "Fine-tuned BERT model to classify user queries into 40+ intent categories "
                    "for the in-app chatbot, achieving 94% accuracy."
                ),
                "role": "NLP Engineer",
                "team_size": 3,
                "start_date": datetime.date(2023, 6, 1),
                "end_date": None,
                "is_current": True,
                "skills": ["Python", "PyTorch", "Machine Learning"],
            },
        ],
        "education": [
            {
                "degree": "M.Tech in Data Science",
                "institution": "IIT Hyderabad",
                "start_year": 2019,
                "end_year": 2021,
                "grade": "9.1 CGPA",
            },
            {
                "degree": "B.Sc in Mathematics",
                "institution": "Delhi University",
                "start_year": 2016,
                "end_year": 2019,
                "grade": "82%",
            },
        ],
        "certifications": [
            {
                "name": "TensorFlow Developer Certificate",
                "issuer": "Google",
                "issue_date": datetime.date(2022, 3, 5),
                "expiry_date": datetime.date(2025, 3, 5),
                "credential_url": "https://www.tensorflow.org/certificate",
            },
            {
                "name": "Deep Learning Specialization",
                "issuer": "DeepLearning.AI / Coursera",
                "issue_date": datetime.date(2021, 5, 12),
                "expiry_date": None,
                "credential_url": "https://coursera.org/specializations/deep-learning",
            },
        ],
    },
    # ── incomplete ─────────────────────────────────────────────────────────
    {
        "email": "karan.verma@talentexe.demo",
        "full_name": "Karan Verma",
        "designation": "DevOps Engineer",
        "department": "Infrastructure",
        "location": "Pune, India",
        "experience_years": 6.0,
        "profile_status": "incomplete",
        "summary": (
            "Experienced DevOps engineer with a strong background in cloud infrastructure, "
            "CI/CD automation, and SRE practices. Reduced deployment frequency from weekly to "
            "multiple times per day at previous roles using GitOps and ArgoCD."
        ),
        "languages": [
            {"name": "English", "proficiency": "Fluent"},
            {"name": "Hindi", "proficiency": "Native"},
            {"name": "Marathi", "proficiency": "Conversational"},
        ],
        "linkedin_url": "https://linkedin.com/in/karan-verma-demo",
        "github_url": "https://github.com/karan-verma-demo",
        "portfolio_url": "",
        "skills": [
            {"name": "Kubernetes", "category": "DevOps", "level": "Expert", "years": 4.0, "primary": True},
            {"name": "Terraform", "category": "DevOps", "level": "Expert", "years": 3.0, "primary": True},
            {"name": "AWS", "category": "Cloud", "level": "Expert", "years": 5.0, "primary": False},
            {"name": "Docker", "category": "DevOps", "level": "Expert", "years": 5.0, "primary": False},
            {"name": "Python", "category": "Language", "level": "Intermediate", "years": 3.0, "primary": False},
        ],
        "experience": [
            {
                "company_name": "Infosys",
                "designation": "Senior DevOps Engineer",
                "employment_type": "Full-Time",
                "start_date": datetime.date(2021, 4, 1),
                "end_date": None,
                "is_current": True,
                "location": "Pune, India",
                "description": (
                    "Managing multi-region EKS clusters for 15 client workloads. "
                    "Implemented GitOps with ArgoCD cutting release cycle from 5 days to 4 hours."
                ),
            },
            {
                "company_name": "Tech Mahindra",
                "designation": "DevOps Engineer",
                "employment_type": "Full-Time",
                "start_date": datetime.date(2018, 6, 1),
                "end_date": datetime.date(2021, 3, 31),
                "is_current": False,
                "location": "Pune, India",
                "description": (
                    "Built and maintained Jenkins-based CI/CD pipelines for 8 microservices. "
                    "Migrated on-prem workloads to AWS saving 40% on infrastructure costs."
                ),
            },
        ],
        "projects": [
            {
                "name": "Multi-Region EKS Platform",
                "client_name": "Infosys (Client: BFSI)",
                "description": (
                    "Designed and deployed a multi-region Kubernetes platform on AWS EKS with "
                    "Istio service mesh, Prometheus/Grafana observability stack, and auto-scaling."
                ),
                "role": "Lead DevOps Engineer",
                "team_size": 7,
                "start_date": datetime.date(2021, 9, 1),
                "end_date": datetime.date(2023, 3, 31),
                "is_current": False,
                "skills": ["Kubernetes", "Terraform", "AWS"],
            },
            {
                "name": "Cloud Migration – On-prem to AWS",
                "client_name": "Tech Mahindra (Client: Retail)",
                "description": (
                    "Lift-and-shift migration of 20+ legacy services to AWS using Terraform IaC. "
                    "Achieved 99.95% uptime SLA post-migration."
                ),
                "role": "DevOps Engineer",
                "team_size": 5,
                "start_date": datetime.date(2019, 6, 1),
                "end_date": datetime.date(2020, 12, 31),
                "is_current": False,
                "skills": ["Terraform", "AWS", "Docker"],
            },
        ],
        "education": [
            {
                "degree": "B.E. in Electronics & Telecommunication",
                "institution": "Pune Institute of Computer Technology",
                "start_year": 2014,
                "end_year": 2018,
                "grade": "7.9 CGPA",
            }
        ],
        "certifications": [
            {
                "name": "AWS Certified Solutions Architect – Professional",
                "issuer": "Amazon Web Services",
                "issue_date": datetime.date(2022, 11, 10),
                "expiry_date": datetime.date(2025, 11, 10),
                "credential_url": "https://aws.amazon.com/certification/",
            },
            {
                "name": "Certified Kubernetes Administrator (CKA)",
                "issuer": "Cloud Native Computing Foundation",
                "issue_date": datetime.date(2021, 7, 22),
                "expiry_date": datetime.date(2024, 7, 22),
                "credential_url": "https://www.cncf.io/certification/cka/",
            },
        ],
    },
    {
        "email": "neha.patel@talentexe.demo",
        "full_name": "Neha Patel",
        "designation": "Product Designer",
        "department": "Design",
        "location": "Ahmedabad, India",
        "experience_years": 2.0,
        "profile_status": "incomplete",
        "summary": (
            "Creative product designer focused on B2B SaaS with expertise in Figma, "
            "design systems, and user research. Believes great design is invisible — "
            "it just makes things work beautifully."
        ),
        "languages": [
            {"name": "English", "proficiency": "Fluent"},
            {"name": "Hindi", "proficiency": "Native"},
            {"name": "Gujarati", "proficiency": "Native"},
        ],
        "linkedin_url": "https://linkedin.com/in/neha-patel-demo",
        "github_url": "",
        "portfolio_url": "https://nehapatel.design",
        "skills": [
            {"name": "Figma", "category": "Design", "level": "Expert", "years": 2.0, "primary": True},
            {"name": "UI/UX Design", "category": "Design", "level": "Expert", "years": 2.0, "primary": True},
            {"name": "User Research", "category": "Design", "level": "Intermediate", "years": 1.5, "primary": False},
            {"name": "Prototyping", "category": "Design", "level": "Intermediate", "years": 2.0, "primary": False},
        ],
        "experience": [
            {
                "company_name": "Zoho",
                "designation": "Product Designer",
                "employment_type": "Full-Time",
                "start_date": datetime.date(2023, 3, 1),
                "end_date": None,
                "is_current": True,
                "location": "Chennai, India",
                "description": (
                    "Redesigned the Zoho CRM mobile app onboarding flow, improving "
                    "activation rate by 28%. Maintains the product design system for mobile."
                ),
            },
            {
                "company_name": "Wingify",
                "designation": "UX Design Intern",
                "employment_type": "Internship",
                "start_date": datetime.date(2022, 6, 1),
                "end_date": datetime.date(2022, 11, 30),
                "is_current": False,
                "location": "Remote",
                "description": (
                    "Conducted user interviews and usability tests for VWO's A/B testing dashboard. "
                    "Delivered wireframes and prototypes for 3 new features."
                ),
            },
        ],
        "projects": [
            {
                "name": "CRM Mobile App Redesign",
                "client_name": "Zoho",
                "description": (
                    "End-to-end redesign of the mobile CRM app — from user research and journey mapping "
                    "to high-fidelity Figma prototypes and developer handoff."
                ),
                "role": "Lead Designer",
                "team_size": 3,
                "start_date": datetime.date(2023, 5, 1),
                "end_date": datetime.date(2023, 10, 31),
                "is_current": False,
                "skills": ["Figma", "UI/UX Design", "User Research"],
            },
            {
                "name": "Design System – Zoho Mobile",
                "client_name": "Zoho",
                "description": (
                    "Built and documented a mobile-first component library (40+ components) "
                    "adopted by 4 Zoho mobile products."
                ),
                "role": "Designer",
                "team_size": 2,
                "start_date": datetime.date(2024, 1, 1),
                "end_date": None,
                "is_current": True,
                "skills": ["Figma", "Prototyping"],
            },
        ],
        "education": [
            {
                "degree": "B.Des in Interaction Design",
                "institution": "National Institute of Design, Ahmedabad",
                "start_year": 2018,
                "end_year": 2022,
                "grade": "Distinction",
            }
        ],
        "certifications": [
            {
                "name": "Google UX Design Professional Certificate",
                "issuer": "Google / Coursera",
                "issue_date": datetime.date(2022, 12, 1),
                "expiry_date": None,
                "credential_url": "https://coursera.org/professional-certificates/google-ux-design",
            }
        ],
    },
    {
        "email": "arjun.nair@talentexe.demo",
        "full_name": "Arjun Nair",
        "designation": "Full Stack Developer",
        "department": "Engineering",
        "location": "Kochi, India",
        "experience_years": 4.0,
        "profile_status": "incomplete",
        "summary": (
            "Full stack developer with 4 years of experience building scalable web apps "
            "using Node.js, React, and PostgreSQL. Enjoys taking products from 0-to-1 "
            "and working across the entire delivery lifecycle."
        ),
        "languages": [
            {"name": "English", "proficiency": "Fluent"},
            {"name": "Malayalam", "proficiency": "Native"},
            {"name": "Hindi", "proficiency": "Conversational"},
        ],
        "linkedin_url": "https://linkedin.com/in/arjun-nair-demo",
        "github_url": "https://github.com/arjun-nair-demo",
        "portfolio_url": "https://arjunnair.dev",
        "skills": [
            {"name": "Node.js", "category": "Backend", "level": "Expert", "years": 4.0, "primary": True},
            {"name": "React", "category": "Frontend", "level": "Expert", "years": 3.0, "primary": True},
            {"name": "PostgreSQL", "category": "Database", "level": "Intermediate", "years": 3.0, "primary": False},
            {"name": "TypeScript", "category": "Language", "level": "Intermediate", "years": 2.0, "primary": False},
            {"name": "AWS", "category": "Cloud", "level": "Beginner", "years": 1.0, "primary": False},
        ],
        "experience": [
            {
                "company_name": "UST Global",
                "designation": "Full Stack Developer",
                "employment_type": "Full-Time",
                "start_date": datetime.date(2022, 1, 10),
                "end_date": None,
                "is_current": True,
                "location": "Kochi, India",
                "description": (
                    "Building internal workflow automation tools for a US healthcare client. "
                    "Delivered 3 production features using Node.js, React, and PostgreSQL."
                ),
            },
            {
                "company_name": "Qburst Technologies",
                "designation": "Software Engineer",
                "employment_type": "Full-Time",
                "start_date": datetime.date(2020, 8, 1),
                "end_date": datetime.date(2021, 12, 31),
                "is_current": False,
                "location": "Kochi, India",
                "description": (
                    "Developed REST APIs and React UIs for a logistics SaaS product. "
                    "Integrated third-party shipping providers (FedEx, DHL) via webhook pipeline."
                ),
            },
        ],
        "projects": [
            {
                "name": "Healthcare Workflow Automation",
                "client_name": "UST Global (US Healthcare Client)",
                "description": (
                    "Web app to automate prior-authorisation workflows for insurance claims, "
                    "reducing processing time from 3 days to 4 hours. HIPAA-compliant architecture."
                ),
                "role": "Full Stack Developer",
                "team_size": 8,
                "start_date": datetime.date(2022, 4, 1),
                "end_date": None,
                "is_current": True,
                "skills": ["Node.js", "React", "PostgreSQL"],
            },
            {
                "name": "Logistics Shipping Integration",
                "client_name": "Qburst (Logistics SaaS)",
                "description": (
                    "Real-time shipment tracking module integrating FedEx, DHL, and BlueDart APIs "
                    "using webhooks and a PostgreSQL event store."
                ),
                "role": "Backend Developer",
                "team_size": 4,
                "start_date": datetime.date(2021, 3, 1),
                "end_date": datetime.date(2021, 12, 31),
                "is_current": False,
                "skills": ["Node.js", "PostgreSQL", "TypeScript"],
            },
        ],
        "education": [
            {
                "degree": "B.Tech in Computer Science",
                "institution": "College of Engineering, Trivandrum",
                "start_year": 2016,
                "end_year": 2020,
                "grade": "8.4 CGPA",
            }
        ],
        "certifications": [
            {
                "name": "MongoDB Certified Developer",
                "issuer": "MongoDB University",
                "issue_date": datetime.date(2022, 9, 14),
                "expiry_date": datetime.date(2025, 9, 14),
                "credential_url": "https://university.mongodb.com/certification/developer",
            }
        ],
    },
]


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Seed 6 dummy employee accounts with full profile data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing seed users before creating new ones.",
        )

    def handle(self, *args, **options):
        from apps.users.models import UserProfile
        from apps.profiles.models import (
            EmployeeProfile, SkillMaster, EmployeeSkill,
            EmployeeExperience, Project, ProjectSkill,
            Certification, Education,
        )
        from apps.reviews.models import ProfileReview

        if options["clear"]:
            emails = [e["email"] for e in EMPLOYEES]
            deleted, _ = UserProfile.objects.filter(email__in=emails).delete()
            self.stdout.write(self.style.WARNING(f"Cleared {deleted} existing seed records."))
            # Also remove from Supabase auth
            try:
                client = get_supabase_admin_client()
                for user in client.auth.admin.list_users():
                    if user.email in emails:
                        client.auth.admin.delete_user(str(user.id))
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"Could not clean Supabase auth: {exc}"))

        for emp_data in EMPLOYEES:
            email = emp_data["email"]
            self.stdout.write(f"\nProcessing {emp_data['full_name']} ({email}) …")

            # ── 1. Supabase Auth user ──────────────────────────────────────
            try:
                user_id, temp_pw = create_supabase_user(email, emp_data["full_name"], "employee")
                self.stdout.write(f"  ✓ Supabase auth user created  (password: {temp_pw})")
            except Exception as exc:
                err_msg = str(exc)
                if "already" in err_msg.lower() or "exists" in err_msg.lower():
                    self.stdout.write(self.style.WARNING(f"  ⚠ Auth user already exists, skipping: {email}"))
                    # Try to find existing UserProfile
                    try:
                        profile = UserProfile.objects.get(email=email)
                        self.stdout.write(f"  ✓ Found existing UserProfile ({profile.id})")
                        continue
                    except UserProfile.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f"  ✗ No UserProfile found for {email}, skipping."))
                        continue
                else:
                    self.stdout.write(self.style.ERROR(f"  ✗ Failed to create Supabase user: {exc}"))
                    continue

            with transaction.atomic():
                # ── 2. UserProfile ─────────────────────────────────────────
                profile = UserProfile.objects.create(
                    id=user_id,
                    email=email,
                    full_name=emp_data["full_name"],
                    role="employee",
                    designation=emp_data["designation"],
                    department=emp_data["department"],
                    location=emp_data["location"],
                    experience_years=emp_data["experience_years"],
                    profile_status=emp_data["profile_status"],
                    must_change_password=False,
                    is_active=True,
                )
                self.stdout.write(f"  ✓ UserProfile created ({profile.id})")

                # ── 3. EmployeeProfile ─────────────────────────────────────
                EmployeeProfile.objects.create(
                    profile=profile,
                    summary=emp_data["summary"],
                    languages=emp_data["languages"],
                    linkedin_url=emp_data.get("linkedin_url", ""),
                    github_url=emp_data.get("github_url", ""),
                    portfolio_url=emp_data.get("portfolio_url", ""),
                )
                self.stdout.write("  ✓ EmployeeProfile created")

                # ── 4. Skills ──────────────────────────────────────────────
                for sk in emp_data["skills"]:
                    master, _ = SkillMaster.objects.get_or_create(
                        name=sk["name"],
                        defaults={"category": sk["category"]},
                    )
                    EmployeeSkill.objects.get_or_create(
                        profile=profile,
                        skill=master,
                        defaults={
                            "proficiency_level": sk["level"],
                            "years_of_experience": sk["years"],
                            "is_primary": sk["primary"],
                            "source": "manual",
                        },
                    )
                self.stdout.write(f"  ✓ {len(emp_data['skills'])} skills added")

                # ── 5. Experience ──────────────────────────────────────────
                for exp in emp_data["experience"]:
                    EmployeeExperience.objects.create(profile=profile, **exp)
                self.stdout.write(f"  ✓ {len(emp_data['experience'])} experience entries added")

                # ── 6. Projects + ProjectSkills ───────────────────────────
                for proj_data in emp_data["projects"]:
                    skill_names = proj_data.pop("skills", [])
                    project = Project.objects.create(profile=profile, **proj_data)
                    for skill_name in skill_names:
                        try:
                            skill_obj = SkillMaster.objects.get(name=skill_name)
                            ProjectSkill.objects.get_or_create(project=project, skill=skill_obj)
                        except SkillMaster.DoesNotExist:
                            pass
                self.stdout.write(f"  ✓ {len(emp_data['projects'])} projects added")

                # ── 7. Education ───────────────────────────────────────────
                for edu in emp_data["education"]:
                    Education.objects.create(profile=profile, **edu)
                self.stdout.write(f"  ✓ {len(emp_data['education'])} education entries added")

                # ── 8. Certifications ──────────────────────────────────────
                for cert in emp_data["certifications"]:
                    Certification.objects.create(profile=profile, **cert)
                self.stdout.write(f"  ✓ {len(emp_data['certifications'])} certifications added")

                # ── 9. ProfileReview for submitted employees ───────────────
                if emp_data["profile_status"] == "submitted":
                    ProfileReview.objects.create(profile=profile, status="pending")
                    self.stdout.write("  ✓ ProfileReview (pending) created")

            self.stdout.write(
                self.style.SUCCESS(
                    f"  → {emp_data['full_name']} seeded  [status: {emp_data['profile_status']}]"
                )
            )

        self.stdout.write(self.style.SUCCESS("\n✅ Seeding complete — 6 employees created.\n"))
        self.stdout.write("Login password for all seed users: " + self.style.WARNING(SEED_PASSWORD))

        # ── Auto-generate embeddings for approved profiles ─────────────────
        self.stdout.write("\nGenerating embeddings for approved profiles …")
        from apps.ai_integration.profile_text_builder import build_searchable_text
        from apps.ai_integration.embedder import generate_embedding
        from django.db import connection as db_conn

        approved_profiles = UserProfile.objects.filter(
            email__in=[e["email"] for e in EMPLOYEES if e["profile_status"] == "approved"]
        )
        for profile in approved_profiles:
            try:
                text = build_searchable_text(profile)
                if not text.strip():
                    continue
                embedding = generate_embedding(text)
                embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
                with db_conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO employee_embeddings (id, profile_id, embedding_type, embedding, searchable_text, updated_at)
                        VALUES (gen_random_uuid(), %s, 'profile', %s::vector, %s, NOW())
                        ON CONFLICT (profile_id, embedding_type)
                        DO UPDATE SET embedding = EXCLUDED.embedding,
                                      searchable_text = EXCLUDED.searchable_text,
                                      updated_at = NOW()
                        """,
                        [str(profile.id), embedding_str, text],
                    )
                self.stdout.write(f"  ✓ Embedding stored for {profile.full_name}")
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"  ⚠ Embedding failed for {profile.full_name}: {exc}"))

        self.stdout.write(self.style.SUCCESS("Embeddings done.\n"))
