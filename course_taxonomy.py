"""
Course Taxonomy and Skill Category Mapping for SkillQuery.
Separates skills into distinct, meaningful categories:
- Frontend Development (HTML/CSS, JS, React, Web Tech)
- Backend Development (Node.js, Express.js, Django, Flask, Spring Boot, PHP)
- Programming Languages (C, C++, Python, Java, JavaScript)
- Database Management (Database Programming, DBMS, SQL)
- Data Structures and Algorithms (DSA)
- Operating Systems (OS)
- Computer Networks (Networking)
- Linux and Systems
- Cloud and DevOps
- AI and Machine Learning
- UI/UX Design
- Full Stack Development
- Mobile Development
"""

import re
from typing import Optional, List, Dict, Any

# ==============================================================================
# 1. CANONICAL SKILL CATEGORIES
# ==============================================================================

TAXONOMY: Dict[str, Dict[str, Any]] = {
    "frontend": {
        "key": "frontend",
        "display_name": "Frontend Development",
        "aliases": [
            "frontend", "front end", "front-end", "client side", "client-side",
            "web development", "web dev", "frontend development", "frontend dev"
        ],
        "description": "HTML / CSS, Java Script, React, Web Technology (CSE Core), and Modern Web Applications",
        "verticals": [
            "HTML / CSS",
            "Java Script",
            "React",
            "UI UX",
            "Web Technology (core concept)(PS-CSE)",
            "22CB008 - MODERN WEB APPLICATIONS",
            "Software Hackathon 2026"
        ],
        "courses": [
            "HTML / CSS - Level 1",
            "Java Script - Level 1",
            "React - Level 1",
            "Web Technology (CSE - core concept) - Level 1",
            "Web Technology (CSE - core concept) - Level 2",
            "Web Technology (CSE - core concept) - Level 3",
            "UNIT 1-22CB008 - MODERN WEB APPLICATIONS",
            "UNIT 2-22CB008 - MODERN WEB APPLICATIONS",
            "UNIT 3-22CB008 - MODERN WEB APPLICATIONS",
            "UNIT 4-22CB008 - MODERN WEB APPLICATIONS",
            "UNIT 5-22CB008 - MODERN WEB APPLICATIONS",
            "Web Design & User Interface Engineering"
        ],
        "sql_condition": """(
            vertical_name IN ('HTML / CSS', 'Java Script', 'React', 'UI UX', 'Web Technology (core concept)(PS-CSE)', '22CB008 - MODERN WEB APPLICATIONS')
            OR course_name IN ('HTML / CSS - Level 1', 'Java Script - Level 1', 'React - Level 1', 'Web Design & User Interface Engineering')
            OR vertical_name ILIKE '%UI UX%'
            OR course_name ILIKE '%UI/UX%'
            OR vertical_name ILIKE '%Web Technology%'
        )"""
    },

    "backend": {
        "key": "backend",
        "display_name": "Backend Development",
        "aliases": [
            "backend", "back end", "back-end", "server side", "server-side",
            "backend development", "backend dev", "server development",
            "nodejs", "node.js", "node", "expressjs", "express.js", "express",
            "django", "flask", "spring boot", "springboot", "spring", "php"
        ],
        "description": "Node.js, Express.js, Django, Flask, Spring Boot, and PHP backend development. (Python, Java, Databases, and Networks are classified under their respective specialized domains)",
        "verticals": [
            "Node.js", "Express.js", "Django", "Flask", "Spring Boot", "PHP"
        ],
        "courses": [
            "Node.js", "Express.js", "Django", "Flask", "Spring Boot", "PHP backend development"
        ],
        # Verified backend framework queries
        "sql_condition": """(
            vertical_name ILIKE ANY(ARRAY['%Node%', '%Express%', '%Django%', '%Flask%', '%Spring Boot%', '%PHP%'])
            OR course_name ILIKE ANY(ARRAY['%Node%', '%Express%', '%Django%', '%Flask%', '%Spring Boot%', '%PHP%'])
        )"""
    },

    "programming_languages": {
        "key": "programming_languages",
        "display_name": "Programming Languages",
        "aliases": [
            "programming languages", "programming language", 
            "coding languages", "coding language", "coding courses"
        ],
        "description": "C Programming, C++, Java, Python, and JavaScript",
        "verticals": [
            "C Programming",
            "Programming C++",
            "Programming Java",
            "Programming Python",
            "Java Script"
        ],
        "courses": [
            "C Programming Level - 1", "C Programming Level - 2", "C Programming Level - 3A", "C Programming Level - 3B", "C Programming Level - 4", "C Programming Level - 5", "C Programming Level - 6",
            "Programming C++ Level - 1", "Programming C++ - Level 2", "Programming C++ - Level 3", "Programming C++ - Level 4", "Programming C++ - Level 5",
            "Programming Java Level - 1", "Programming Java Level - 2", "Programming Java Level - 3", "Programming Java Level - 4",
            "Programming Python Level - 1", "Programming Python Level - 2", "Programming Python Level - 3", "Programming Python Level - 4", "Programming Python Level - 5",
            "Java Script - Level 1"
        ],
        "sql_condition": """(
            vertical_name IN ('C Programming', 'Programming C++', 'Programming Java', 'Programming Python', 'Java Script')
            OR course_name ILIKE '%C Programming%'
            OR course_name ILIKE '%Programming C++%'
            OR course_name ILIKE '%Programming Java%'
            OR course_name ILIKE '%Programming Python%'
            OR course_name ILIKE '%Java Script%'
        )"""
    },

    "database": {
        "key": "database",
        "display_name": "Database Management",
        "aliases": [
            "database", "databases", "dbms", "sql", "database management", 
            "db", "database programming", "relational database", "mysql", "postgresql", "mongodb"
        ],
        "description": "Database Programming (Levels 1-7) and DBMS Core Concepts (Levels 1-3)",
        "verticals": [
            "Database Programming",
            "DBMS - Core Concept (PS-CSE)"
        ],
        "courses": [
            "Database Programming Level - 1", "Database Programming Level - 2", "Database Programming Level - 3", "Database Programming Level - 4", "Database Programming Level - 5", "Database Programming Level - 6", "Database Programming Level - 7",
            "DBMS Level 1 - (CSE - core concept)", "DBMS Level 2 - (CSE - core concept)", "DBMS Leve 3 - (CSE - core concept)"
        ],
        "sql_condition": """(
            vertical_name IN ('Database Programming', 'DBMS - Core Concept (PS-CSE)')
            OR course_name ILIKE '%Database Programming%'
            OR course_name ILIKE '%DBMS%'
        )"""
    },

    "dsa": {
        "key": "dsa",
        "display_name": "Data Structures & Algorithms",
        "aliases": [
            "dsa", "data structures", "data structure", "algorithms", "data structures and algorithms"
        ],
        "description": "Data Structures (Levels 1-5), Data Structures Core Concepts (CSE), and Data Structures using Java",
        "verticals": [
            "Data Structure",
            "Data Structure - Core Conepts (PS-CSE)",
            "Data Structure using Java"
        ],
        "courses": [
            "Data Structure - 1", "Data Structure - 2", "Data Structure - 3", "Data Structure - 4", "Data Structure - 5",
            "Data Structure Level 1 - (CSE - core concept)", "Data Structure Level 2 - (CSE - core concept)", "Data Structure Level 3 - (CSE - core concept)",
            "Data Structure using Java - Level 1"
        ],
        "sql_condition": """(
            vertical_name ILIKE '%Data Structure%'
            OR course_name ILIKE '%Data Structure%'
        )"""
    },

    "os": {
        "key": "os",
        "display_name": "Operating Systems",
        "aliases": [
            "operating systems", "operating system", "os", "rtos"
        ],
        "description": "Operating Systems Core Concepts (CSE Levels 1-3) and Real-Time Operating Systems",
        "verticals": [
            "OS - (Core concept)(PS-CSE)",
            "22EC004 - REAL-TIME OPERATING SYSTEMS"
        ],
        "courses": [
            "OS - (CSE - Core Concept) Level 1", "OS - (CSE - Core Concept) Level 2", "OS - (CSE - Core Concept) Level 3",
            "UNIT 1-22EC004 - REAL-TIME OPERATING SYSTEMS", "UNIT 2-22EC004 - REAL-TIME OPERATING SYSTEMS", "UNIT 3-22EC004 - REAL-TIME OPERATING SYSTEMS", "UNIT 4-22EC004 - REAL-TIME OPERATING SYSTEMS", "UNIT 5-22EC004 - REAL-TIME OPERATING SYSTEMS"
        ],
        "sql_condition": """(
            vertical_name ILIKE '%OS - %'
            OR course_name ILIKE '%OS - %'
            OR vertical_name ILIKE '%OPERATING SYSTEM%'
            OR course_name ILIKE '%OPERATING SYSTEM%'
        )"""
    },

    "networks": {
        "key": "networks",
        "display_name": "Computer Networks",
        "aliases": [
            "computer networks", "networking", "networks", "network", "computer networking"
        ],
        "description": "Computer Networking (Levels 0-2), Networks Core Concepts (CSE), and Computer Networks & Protocols",
        "verticals": [
            "Computer Networking",
            "Networks - (Core Concepts) (PS-CSE)",
            "22CB601\t-COMPUTER NETWORKS",
            "22EC601\t-COMPUTER NETWORKS AND PROTOCOLS"
        ],
        "courses": [
            "Computer Networking - Level 0", "Computer Networking - Level 1", "Computer Networking - Level 1A", "Computer Networking - Level 2",
            "Networks - (CSE - Core Concepts) Level 1", "Networks - (CSE - Core Concepts) Level 2", "Networks - (CSE - Core Concepts) Level 3",
            "UNIT 1-22CB601\tCOMPUTER NETWORKS", "UNIT 1-22EC601\tCOMPUTER NETWORKS AND PROTOCOLS"
        ],
        "sql_condition": """(
            vertical_name ILIKE '%Networking%'
            OR course_name ILIKE '%Networking%'
            OR vertical_name ILIKE '%COMPUTER NETWORKS%'
            OR course_name ILIKE '%COMPUTER NETWORKS%'
            OR vertical_name ILIKE '%Networks - %'
            OR course_name ILIKE '%Networks - %'
        )"""
    },

    "linux_systems": {
        "key": "linux_systems",
        "display_name": "Linux & Systems",
        "aliases": [
            "linux", "unix", "systems", "linux systems"
        ],
        "description": "Linux (Levels 0-3)",
        "verticals": ["Linux"],
        "courses": ["Linux Level 0", "Linux Level 1", "Linux Level 2", "Linux Level 3"],
        "sql_condition": """(
            vertical_name ILIKE '%Linux%'
            OR course_name ILIKE '%Linux%'
        )"""
    },

    "ui_ux": {
        "key": "ui_ux",
        "display_name": "UI/UX Design",
        "aliases": [
            "ui", "ux", "uiux", "ui/ux", "user interface", "user experience", "ui design"
        ],
        "description": "UI/UX (Levels 1-5) and Web Design & User Interface Engineering",
        "verticals": ["UI UX", "Software Hackathon 2026"],
        "courses": [
            "UI/UX Level -1", "UI/UX Level - 2", "UI/UX Level - 3", "UI/UX Level - 4", "UI/UX Level - 5",
            "Web Design & User Interface Engineering"
        ],
        "sql_condition": """(
            vertical_name ILIKE '%UI UX%'
            OR course_name ILIKE '%UI/UX%'
            OR course_name ILIKE '%User Interface%'
        )"""
    },

    "full_stack": {
        "key": "full_stack",
        "display_name": "Full Stack Development",
        "aliases": [
            "full stack", "fullstack", "full-stack", "full stack development", "full stack developer"
        ],
        "description": "Vibe Coding & Full Stack Development, Full Stack & DevOps, and Modern Web Applications",
        "verticals": [
            "Software Hackathon 2026",
            "Special Lab",
            "22CB008 - MODERN WEB APPLICATIONS"
        ],
        "courses": [
            "Vibe Coding & Full Stack Development",
            "Full Stack & DevOps (PIC113)",
            "UNIT 1-22CB008 - MODERN WEB APPLICATIONS",
            "UNIT 2-22CB008 - MODERN WEB APPLICATIONS",
            "UNIT 3-22CB008 - MODERN WEB APPLICATIONS",
            "UNIT 4-22CB008 - MODERN WEB APPLICATIONS",
            "UNIT 5-22CB008 - MODERN WEB APPLICATIONS"
        ],
        "sql_condition": """(
            course_name ILIKE '%Full Stack%' 
            OR course_name ILIKE '%Vibe Coding%'
            OR vertical_name ILIKE '%Full Stack%'
            OR vertical_name = '22CB008 - MODERN WEB APPLICATIONS'
        )"""
    },

    "cloud_devops": {
        "key": "cloud_devops",
        "display_name": "Cloud & DevOps",
        "aliases": [
            "cloud", "devops", "cloud computing", "git", "github", "version control", "cloud automation"
        ],
        "description": "Cloud Automation Tools, Version Control (Git & GitHub), and Cloud & Cyber Security",
        "verticals": [
            "Version control - Git, Github",
            "Special Lab",
            "22CD016/22CS016/22CT016/22IS010/22IT016  CLOUD AUTOMATION TOOLS AND APPLICATIONS"
        ],
        "courses": [
            "Version control - Git, Github Level 0",
            "Cloud & Cyber Security",
            "UNIT 1,2 - 22CD016/22CS016/22CT016/22IS010/22IT016  CLOUD AUTOMATION TOOLS AND APPLICATIONS",
            "UNIT 3,4 - 22CD016/22CS016/22CT016/22IS010/22IT016  CLOUD AUTOMATION TOOLS AND APPLICATIONS"
        ],
        "sql_condition": """(
            vertical_name ILIKE '%CLOUD AUTOMATION%'
            OR course_name ILIKE '%CLOUD AUTOMATION%'
            OR vertical_name ILIKE '%Version control%'
            OR course_name ILIKE '%Git%'
            OR course_name ILIKE '%Cloud%'
        )"""
    },

    "ai_ml": {
        "key": "ai_ml",
        "display_name": "AI & Machine Learning",
        "aliases": [
            "ai", "ml", "artificial intelligence", "machine learning", "deep learning", 
            "neural networks", "aiml", "ai/ml"
        ],
        "description": "Machine Learning, Deep Learning, Maths for Machine Learning, and AI Development",
        "verticals": [
            "AI - Machine Learning",
            "AI - Deep Learning",
            "AI - Maths for Machine Learning",
            "Software Hackathon 2026",
            "Special Lab"
        ],
        "courses": [
            "Machine Learning - Level 1", "Machine Learning - Level 2",
            "Deep Learning - Level 1",
            "Maths for Machine Learning Level - 1A",
            "AI Development",
            "Artificial Intelligence (PIC111)"
        ],
        "sql_condition": """(
            vertical_name ILIKE '%AI - %'
            OR vertical_name ILIKE '%Machine Learning%'
            OR vertical_name ILIKE '%Deep Learning%'
            OR course_name ILIKE '%Machine Learning%'
            OR course_name ILIKE '%Deep Learning%'
            OR course_name ILIKE '%Artificial Intelligence%'
        )"""
    },

    "data_science": {
        "key": "data_science",
        "display_name": "Data Science & Analytics",
        "aliases": [
            "data science", "data analytics", "datascience", "data scientist", "analytics"
        ],
        "description": "Data Science, Bioinformatics & Data Analytics, and Data Science Core Concepts",
        "verticals": [
            "Data Science",
            "Data Science - (Core concept) (PS-CSE)",
            "Bioinformatics and Data Science",
            "Special Lab"
        ],
        "courses": [
            "Data Science - Level 1", "Data Science Level 0",
            "Data Science - (CSE - Core concept) Level 1", "Data Science - (CSE - Core concept) Level 2", "Data Science - (CSE - Core concept) Level 3",
            "Bioinformatics and Data Analytics - Level 1", "Bioinformatics and Data Analytics - Level 2A",
            "Data Science (PIC112)"
        ],
        "sql_condition": """(
            vertical_name ILIKE '%Data Science%'
            OR course_name ILIKE '%Data Science%'
            OR course_name ILIKE '%Data Analytics%'
        )"""
    },

    "mobile_development": {
        "key": "mobile_development",
        "display_name": "Mobile App Development",
        "aliases": [
            "mobile", "android", "mobile app", "mobile application", "app development"
        ],
        "description": "Mobile App Development - Android (Java) and Mobile Application Design",
        "verticals": [
            "Mobile App Developement - Android (Java)",
            "22CD702 - MOBILE APPLICATION DESIGN AND DEVELOPMENT",
            "22CT702 - MOBILE APPLICATION DEVELOPMENT"
        ],
        "courses": [
            "Mobile App Developement - Android (Java) - Level 0",
            "UNIT 1,2 - 22CD702 - MOBILE APPLICATION DESIGN AND DEVELOPMENT",
            "UNIT 3,4 - 22CD702 - MOBILE APPLICATION DESIGN AND DEVELOPMENT",
            "UNIT 1,2 - 22CT702 - MOBILE APPLICATION DEVELOPMENT",
            "UNIT 3,4 - 22CT702 - MOBILE APPLICATION DEVELOPMENT"
        ],
        "sql_condition": """(
            vertical_name ILIKE '%Mobile App%'
            OR vertical_name ILIKE '%MOBILE APPLICATION%'
            OR course_name ILIKE '%Mobile App%'
            OR course_name ILIKE '%Android%'
        )"""
    }
}

# ==============================================================================
# 2. VERIFIED DEPARTMENT MAPPING
# ==============================================================================

DEPARTMENTS: Dict[str, Dict[str, Any]] = {
    "CS": {
        "code": "CS",
        "name": "Computer Science and Engineering",
        "aliases": ["cse", "computer science", "cs", "comp sci"]
    },
    "IT": {
        "code": "IT",
        "name": "Information Technology",
        "aliases": ["it", "information tech", "infotech"]
    },
    "AD": {
        "code": "AD",
        "name": "Artificial Intelligence and Data Science",
        "aliases": ["aids", "ai&ds", "ai ds", "ai and ds", "ai data science"]
    },
    "AL": {
        "code": "AL",
        "name": "Artificial Intelligence and Machine Learning",
        "aliases": ["aiml", "ai&ml", "ai ml", "ai and ml", "ai machine learning"]
    },
    "EC": {
        "code": "EC",
        "name": "Electronics and Communication Engineering",
        "aliases": ["ece", "ec", "electronics and communication", "electronics"]
    },
    "EE": {
        "code": "EE",
        "name": "Electrical and Electronics Engineering",
        "aliases": ["eee", "ee", "electrical and electronics", "electrical"]
    },
    "EI": {
        "code": "EI",
        "name": "Electronics and Instrumentation Engineering",
        "aliases": ["eie", "ei", "instrumentation"]
    },
    "BM": {
        "code": "BM",
        "name": "Biomedical Engineering",
        "aliases": ["bme", "bm", "biomedical", "bio medical"]
    },
    "BT": {
        "code": "BT",
        "name": "Biotechnology",
        "aliases": ["bt", "biotech", "bio technology"]
    },
    "CB": {
        "code": "CB",
        "name": "Computer Science and Business Systems",
        "aliases": ["csbs", "cb", "cs and bs", "computer science business"]
    },
    "CD": {
        "code": "CD",
        "name": "Computer Science and Design",
        "aliases": ["csd", "cd", "cs design"]
    },
    "CT": {
        "code": "CT",
        "name": "Computer Technology",
        "aliases": ["ctech", "ct", "computer tech"]
    },
    "ME": {
        "code": "ME",
        "name": "Mechanical Engineering",
        "aliases": ["mech", "mechanical", "me"]
    },
    "MZ": {
        "code": "MZ",
        "name": "Mechatronics Engineering",
        "aliases": ["mechatronics", "mz"]
    },
    "SE": {
        "code": "SE",
        "name": "Information Science and Engineering",
        "aliases": ["ise", "se", "information science"]
    },
    "CE": {
        "code": "CE",
        "name": "Civil Engineering",
        "aliases": ["civil", "ce"]
    },
    "AG": {
        "code": "AG",
        "name": "Agricultural Engineering",
        "aliases": ["agri", "agriculture", "agricultural", "ag"]
    },
    "FD": {
        "code": "FD",
        "name": "Food Technology",
        "aliases": ["food tech", "food technology", "fd"]
    },
    "FT": {
        "code": "FT",
        "name": "Fashion Technology",
        "aliases": ["fashion tech", "fashion technology", "ft"]
    }
}

# ==============================================================================
# 3. HELPER LOOKUP & RESOLUTION FUNCTIONS
# ==============================================================================

def normalize_text(text: str) -> str:
    """Lowercase and strip punctuation for loose matching."""
    return re.sub(r'[^a-z0-9]', '', str(text).lower())

def resolve_category(query: str) -> Optional[Dict[str, Any]]:
    """
    Identifies if a natural language question mentions a skill category.
    Returns category dict if matched, None otherwise.
    """
    q_norm = f" {query.lower()} "
    
    candidates = []
    for cat_key, cat_data in TAXONOMY.items():
        for alias in cat_data["aliases"]:
            pattern = r'(?:\b|\s)' + re.escape(alias) + r'(?:\b|\s)'
            if re.search(pattern, q_norm, re.IGNORECASE):
                candidates.append((len(alias), cat_data))
    
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
        
    return None

def resolve_department(query: str) -> Optional[Dict[str, Any]]:
    """
    Detects if a query contains a department name, code, or alias (e.g., 'CSE', 'AIDS', 'Mechanical').
    Carefully handles common English words like 'me' and 'it' so they don't trigger false positives.
    """
    q_norm = f" {query.lower()} "
    
    # Common English words that shouldn't match as bare lowercase words
    COMMON_WORD_DEPTS = {
        "ME": {
            "dept_data": DEPARTMENTS["ME"],
            "explicit_patterns": [
                r'\b(?:in|from|of|for|dept|department|branch)\s+me\b',
                r'\bme\s+(?:dept|department|branch|students?|candidates?)\b',
                r'\bmech\b',
                r'\bmechanical\b'
            ],
            "case_pattern": r'\bME\b'
        },
        "IT": {
            "dept_data": DEPARTMENTS["IT"],
            "explicit_patterns": [
                r'\b(?:in|from|of|for|dept|department|branch)\s+it\b',
                r'\bit\s+(?:dept|department|branch|students?|candidates?)\b',
                r'\binfotech\b',
                r'\binformation tech(?:nology)?\b'
            ],
            "case_pattern": r'\bIT\b'
        }
    }

    # 1. Check special departments with context patterns or strict case
    for code, spec in COMMON_WORD_DEPTS.items():
        for p in spec["explicit_patterns"]:
            if re.search(p, q_norm, re.IGNORECASE):
                return spec["dept_data"]
        # Case sensitive check if query is not all uppercase
        if not query.isupper() and re.search(spec["case_pattern"], query):
            return spec["dept_data"]

    # 2. Check all other standard departments
    for dept_code, dept_data in DEPARTMENTS.items():
        if dept_code in COMMON_WORD_DEPTS:
            continue
        patterns = [r'\b' + re.escape(dept_code.lower()) + r'\b'] + [
            r'\b' + re.escape(alias.lower()) + r'\b' for alias in dept_data["aliases"]
        ]
        for p in patterns:
            if re.search(p, q_norm, re.IGNORECASE):
                return dept_data
                
    return None

def get_taxonomy_summary() -> str:
    """Returns a short description of supported categories for LLM prompting."""
    lines = []
    for k, v in TAXONOMY.items():
        lines.append(f"- {v['display_name']} ({k}): {v['description']}")
    return "\n".join(lines)
