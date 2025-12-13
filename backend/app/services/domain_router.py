"""
Domain Router Service - Routes queries to specialist models

This service detects the domain of a user query and determines if a
specialist model should be used instead of the default chat model.

Implements:
- Pattern-based detection (fast, handles obvious cases)
- Self-routing support (Gala can request specialist help)
- Model swap coordination with model_manager
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


class Domain(Enum):
    """Supported specialist domains"""
    GENERAL = "general"
    MEDICAL = "medical"
    LEGAL = "legal"
    CODING = "coding"
    MATH = "math"
    FINANCE = "finance"
    SCIENCE = "science"
    CREATIVE = "creative"
    KNOWLEDGE = "knowledge"  # Deep knowledge mode - slower but more capable
    PERSONALITY = "personality"  # Big personality mode - more expressive


@dataclass
class DomainConfig:
    """Configuration for a specialist domain"""
    domain: Domain
    patterns: List[str]  # Regex patterns to match
    keywords: List[str]  # Simple keyword matches
    model: str  # Ollama model name
    model_size: str  # For display (e.g., "7B")
    description: str  # Human-readable description
    enabled: bool = True
    voice: Optional[str] = None  # Optional voice override for this domain


# Default specialist model configurations
# Users can override these in settings
DEFAULT_SPECIALISTS = {
    Domain.MEDICAL: DomainConfig(
        domain=Domain.MEDICAL,
        patterns=[
            r"\b(diagnos|symptom|treatment|medication|disease|illness|patient)\w*\b",
            r"\b(doctor|physician|nurse|hospital|clinic)\b",
            r"\b(prescription|dosage|side.?effect|drug.?interact)\w*\b",
            r"\b(blood.?pressure|heart.?rate|cholesterol|diabetes|cancer)\b",
            r"\b(pain|ache|fever|infection|inflammation)\b",
            r"\b(surgery|procedure|therapy|rehabilitation)\b",
        ],
        keywords=[
            "medical", "health", "healthcare", "medicine", "clinical",
            "diagnosis", "prognosis", "chronic", "acute", "condition",
            "vaccine", "immunization", "antibiotic", "antidepressant",
            "mg", "dosage", "twice daily", "prescription",
        ],
        model="koesn/llama3-openbiollm-8b:latest",  # OpenBioLLM-Llama3-8B
        model_size="8B",
        description="Medical and healthcare specialist (OpenBioLLM)",
        enabled=True,
    ),
    
    Domain.LEGAL: DomainConfig(
        domain=Domain.LEGAL,
        patterns=[
            r"\b(lawsuit|litigation|court|trial|verdict|settlement)\b",
            r"\b(contract|agreement|clause|terms|breach)\b",
            r"\b(attorney|lawyer|counsel|paralegal|judge)\b",
            r"\b(liability|negligence|damages|compensation)\b",
            r"\b(copyright|trademark|patent|intellectual.?property)\b",
            r"\b(criminal|civil|plaintiff|defendant|prosecution)\b",
        ],
        keywords=[
            "legal", "law", "rights", "sue", "lawsuit",
            "court", "judge", "attorney", "lawyer",
            "contract", "agreement", "liability",
            "divorce", "custody", "alimony",
            "arrest", "bail", "sentence",
            "landlord", "tenant", "lease", "eviction",
        ],
        model="qwen3:32b",  # Qwen 3 32B - superior reasoning for legal
        model_size="32B",
        description="Legal and contract specialist (Qwen 3)",
        enabled=True,
    ),
    
    Domain.CODING: DomainConfig(
        domain=Domain.CODING,
        patterns=[
            r"\b(function|method|class|variable|parameter|argument)\b",
            r"\b(error|exception|bug|debug|stack.?trace)\b",
            r"\b(api|endpoint|request|response|json|xml)\b",
            r"\b(database|sql|query|table|join|index)\b",
            r"\b(git|commit|branch|merge|pull.?request)\b",
            r"```\w*\n",  # Code blocks
            r"\b(import|from|require|include)\s+\w+",
        ],
        keywords=[
            "code", "coding", "programming", "developer", "software",
            "python", "javascript", "typescript", "java", "rust", "go",
            "react", "vue", "angular", "node", "django", "flask",
            "algorithm", "data structure", "recursion", "iteration",
            "frontend", "backend", "fullstack", "devops",
            "docker", "kubernetes", "aws", "cloud",
        ],
        model="huihui_ai/qwen3-coder-abliterated:latest",  # Qwen 3 Coder 30B abliterated
        model_size="30B",
        description="Programming and software development specialist (Qwen 3 Coder)",
        enabled=True,
    ),
    
    Domain.MATH: DomainConfig(
        domain=Domain.MATH,
        patterns=[
            r"\b(calculate|compute|solve|evaluate|simplify)\b",
            r"\b(equation|formula|expression|inequality)\b",
            r"\b(derivative|integral|limit|differential)\b",
            r"\b(matrix|vector|determinant|eigenvalue)\b",
            r"\b(probability|statistics|distribution|variance)\b",
            r"[=+\-*/^√∑∫∂]",  # Math symbols
            r"\d+\s*[+\-*/^]\s*\d+",  # Arithmetic expressions
        ],
        keywords=[
            "math", "mathematics", "mathematical", "algebra", "geometry",
            "calculus", "trigonometry", "statistics", "probability",
            "equation", "formula", "theorem", "proof",
            "graph", "function", "variable", "constant",
            "factorial", "permutation", "combination",
        ],
        model="mightykatun/qwen2.5-math:7b",  # Qwen 2.5 Math 7B
        model_size="7B",
        description="Mathematics and calculations specialist (Qwen 2.5 Math)",
        enabled=True,
    ),
    
    Domain.FINANCE: DomainConfig(
        domain=Domain.FINANCE,
        patterns=[
            r"\b(stock|share|equity|bond|fund|etf|portfolio)\b",
            r"\b(invest|investment|trading|market|exchange)\b",
            r"\b(dividend|yield|return|profit|loss|roi)\b",
            r"\b(tax|deduction|credit|irs|filing)\b",
            r"\b(mortgage|loan|interest|principal|apr)\b",
            r"\b(budget|expense|income|savings|retirement)\b",
            r"\$\d+|\d+%",  # Dollar amounts, percentages
        ],
        keywords=[
            "finance", "financial", "money", "banking", "bank",
            "stock", "bond", "investment", "portfolio",
            "401k", "ira", "roth", "pension", "retirement",
            "crypto", "bitcoin", "ethereum", "cryptocurrency",
            "inflation", "recession", "gdp", "economy",
        ],
        model="fingpt:latest",  # FinGPT - finance specialist
        model_size="8B",
        description="Finance and investment specialist (FinGPT)",
        enabled=True,
    ),
    
    Domain.SCIENCE: DomainConfig(
        domain=Domain.SCIENCE,
        patterns=[
            r"\b(hypothesis|experiment|research|study|analysis)\b",
            r"\b(atom|molecule|element|compound|reaction)\b",
            r"\b(cell|dna|rna|protein|gene|chromosome)\b",
            r"\b(force|energy|mass|velocity|acceleration)\b",
            r"\b(evolution|species|ecosystem|biodiversity)\b",
            r"\b(stem|engineering|technical|scientific)\b",
            r"\b(thermodynamics|electromagnetism|optics)\b",
        ],
        keywords=[
            "science", "scientific", "research", "experiment",
            "physics", "chemistry", "biology", "astronomy",
            "quantum", "relativity", "particle", "wave",
            "evolution", "genetics", "neuroscience",
            "climate", "environment", "ecology",
            "stem", "engineering", "technical", "mechanics",
            "circuits", "electronics", "thermodynamics",
        ],
        model="rnj-1:latest",  # Essential AI STEM specialist (8B, excels at code/math/science)
        model_size="8B",
        description="STEM specialist - science, engineering, and technical questions",
        enabled=True,  # Enabled - rnj-1 is excellent for STEM
    ),
    
    Domain.CREATIVE: DomainConfig(
        domain=Domain.CREATIVE,
        patterns=[
            r"\b(write|story|poem|novel|screenplay|script)\b",
            r"\b(character|plot|setting|narrative|dialogue)\b",
            r"\b(creative|imagination|fantasy|fiction)\b",
        ],
        keywords=[
            "write", "writing", "story", "novel", "poem", "poetry",
            "creative", "fiction", "fantasy", "sci-fi",
            "character", "plot", "narrative", "dialogue",
            "roleplay", "scenario", "imagine",
        ],
        model="huihui_ai/qwen3-abliterated:32b",  # Qwen 3 32B abliterated - uncensored creative
        model_size="32B",
        description="Creative writing specialist (Qwen 3 abliterated)",
        enabled=True,
    ),
    
    Domain.KNOWLEDGE: DomainConfig(
        domain=Domain.KNOWLEDGE,
        patterns=[
            r"\b(more\s+knowledgeable|be\s+smarter|think\s+harder|deeper\s+analysis)\b",
            r"\b(use\s+your\s+big\s+brain|really\s+think|comprehensive|thorough)\b",
            r"\b(expert\s+mode|full\s+power|maximum\s+intelligence)\b",
            r"\b(detailed\s+explanation|in[\-\s]?depth|elaborate)\b",
        ],
        keywords=[
            "knowledgeable", "smarter", "deeper", "thorough", "comprehensive",
            "expert mode", "big brain", "think harder", "full power",
            "detailed", "in-depth", "elaborate", "exhaustive",
            "gpt mode", "smart mode", "knowledge mode",
        ],
        model="huihui_ai/gpt-oss-abliterated:20b-q8_0",  # GPT-OSS 20B abliterated - deep knowledge
        model_size="20B",
        description="Deep knowledge mode - slower but more capable (uncensored)",
        enabled=True,
    ),
    
    Domain.PERSONALITY: DomainConfig(
        domain=Domain.PERSONALITY,
        patterns=[
            r"\b(more\s+personality|be\s+expressive|bigger\s+personality)\b",
            r"\b(more\s+character|be\s+fun|liven\s+up|spicy)\b",
            r"\b(dominique|dom\s+mode|sassy|saucy|feisty)\b",
            r"\b(more\s+attitude|less\s+boring|entertaining)\b",
        ],
        keywords=[
            "personality", "expressive", "character", "fun", "entertaining",
            "dominique", "sassy", "spicy", "feisty", "attitude",
            "liven up", "more interesting", "less boring", "more human",
            "personality mode", "fun mode", "expressive mode",
        ],
        model="MartinRizzo/Regent-Dominique:24b-iq3_XXS",  # Dominique 24B - big personality
        model_size="24B",
        description="Big personality mode - expressive and sassy",
        enabled=True,
        voice="af_nicole",  # Nicole (American Female) - matches the personality
    ),
}


class DomainRouter:
    """
    Routes user queries to appropriate specialist models.
    
    Uses a hybrid approach:
    1. Pattern matching for obvious domain indicators
    2. Keyword detection for common terms
    3. Confidence scoring to decide if specialist is needed
    """
    
    def __init__(self):
        self.specialists = DEFAULT_SPECIALISTS.copy()
        self._compiled_patterns: dict[Domain, List[re.Pattern]] = {}
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for performance"""
        for domain, config in self.specialists.items():
            if config.enabled:
                self._compiled_patterns[domain] = [
                    re.compile(p, re.IGNORECASE) for p in config.patterns
                ]
    
    def configure_specialist(self, domain: Domain, model: str, enabled: bool = True):
        """Update specialist model configuration"""
        if domain in self.specialists:
            self.specialists[domain].model = model
            self.specialists[domain].enabled = enabled
            self._compile_patterns()
    
    def detect_domain(self, text: str) -> Tuple[Domain, float, Optional[str], Optional[str]]:
        """
        Detect the domain of a user query.
        
        Returns:
            (domain, confidence, specialist_model, voice_override)
            - domain: The detected domain
            - confidence: 0.0-1.0 confidence score
            - specialist_model: Model name if specialist recommended, None otherwise
            - voice_override: Voice to use for this domain, None to keep current
        """
        text_lower = text.lower()
        scores: dict[Domain, float] = {d: 0.0 for d in Domain}
        
        # Check each enabled specialist
        for domain, config in self.specialists.items():
            if not config.enabled:
                continue
            
            score = 0.0
            
            # Pattern matching (higher weight)
            if domain in self._compiled_patterns:
                for pattern in self._compiled_patterns[domain]:
                    matches = pattern.findall(text)
                    score += len(matches) * 0.3
            
            # Keyword matching (lower weight)
            for keyword in config.keywords:
                if keyword.lower() in text_lower:
                    score += 0.15
            
            scores[domain] = min(score, 1.0)  # Cap at 1.0
        
        # Find highest scoring domain
        best_domain = max(scores, key=scores.get)
        best_score = scores[best_domain]
        
        # Threshold for recommending specialist
        CONFIDENCE_THRESHOLD = 0.4
        
        if best_score >= CONFIDENCE_THRESHOLD and best_domain != Domain.GENERAL:
            specialist = self.specialists[best_domain]
            logger.info(f"Domain detected: {best_domain.value} (confidence: {best_score:.2f})")
            return (best_domain, best_score, specialist.model, specialist.voice)
        
        return (Domain.GENERAL, 1.0 - best_score, None, None)
    
    def parse_self_route(self, text: str) -> Optional[Tuple[Domain, str, Optional[str]]]:
        """
        Parse self-routing tags from Gala's response.
        
        Looks for patterns like:
        - [NEED:medical]
        - [ROUTE:coding]
        - [SPECIALIST:legal]
        
        Returns:
            (domain, model, voice) if routing tag found, None otherwise
        """
        patterns = [
            r'\[NEED:(\w+)\]',
            r'\[ROUTE:(\w+)\]',
            r'\[SPECIALIST:(\w+)\]',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                domain_str = match.group(1).lower()
                try:
                    domain = Domain(domain_str)
                    if domain in self.specialists and self.specialists[domain].enabled:
                        spec = self.specialists[domain]
                        return (domain, spec.model, spec.voice)
                except ValueError:
                    logger.warning(f"Unknown domain in self-route: {domain_str}")
        
        return None
    
    def get_enabled_specialists(self) -> List[dict]:
        """Get list of enabled specialist configurations"""
        return [
            {
                "domain": config.domain.value,
                "model": config.model,
                "model_size": config.model_size,
                "description": config.description,
            }
            for config in self.specialists.values()
            if config.enabled
        ]
    
    def get_routing_prompt_addition(self) -> str:
        """
        Get system prompt addition for self-routing (Option C).
        
        This teaches Gala to recognize when she needs specialist help.
        """
        enabled_domains = [d.value for d, c in self.specialists.items() if c.enabled]
        
        if not enabled_domains:
            return ""
        
        return f"""
SPECIALIST KNOWLEDGE ROUTING:
You have access to specialist knowledge bases for: {', '.join(enabled_domains)}.

If a question requires deep expertise in one of these areas and you're not fully confident in your answer, you may request specialist assistance by including a routing tag in your response:
- [NEED:medical] - for complex medical questions (drug interactions, diagnoses, treatments)
- [NEED:legal] - for legal advice, contracts, rights, litigation
- [NEED:coding] - for programming help, debugging, code review
- [NEED:math] - for complex calculations, proofs, statistics
- [NEED:knowledge] - when user asks you to be more knowledgeable or think deeper
- [NEED:personality] - when user wants more personality, sass, or expressiveness

Only use these tags when the question genuinely requires specialist knowledge. For general questions or topics you're confident about, respond normally.

When you use a routing tag, briefly acknowledge that you're consulting specialist knowledge, e.g.:
"That's an important medical question. Let me consult my medical knowledge base... [NEED:medical]"
"""
    
    def get_handoff_message(self, domain: Domain) -> str:
        """Get a natural transition message when switching to specialist"""
        messages = {
            Domain.MEDICAL: "Let me tap into my medical expertise for this...",
            Domain.LEGAL: "I'll consult my legal knowledge base for this...",
            Domain.CODING: "Switching to my programming specialist mode...",
            Domain.MATH: "Let me engage my mathematical reasoning...",
            Domain.FINANCE: "Consulting my financial analysis capabilities...",
            Domain.SCIENCE: "Let me engage my STEM expertise for this...",
            Domain.CREATIVE: "Engaging creative writing mode...",
            Domain.KNOWLEDGE: "Alright, let me really think about this one...",
            Domain.PERSONALITY: "Oh honey, you want the real me? Here we go!",
        }
        return messages.get(domain, "Let me think about this more carefully...")


# Singleton instance
domain_router = DomainRouter()

