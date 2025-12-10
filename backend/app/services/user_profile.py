"""User Profile Service - Manages onboarding and personal profile data"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ProfileQuestion(BaseModel):
    """A single profile question"""
    id: str
    category: str
    question: str
    follow_up: Optional[str] = None  # Optional follow-up prompt
    priority: int = 5  # 1-10, lower = ask earlier


class ProfileAnswer(BaseModel):
    """A stored answer to a profile question"""
    question_id: str
    question: str
    answer: str
    answered_at: datetime
    category: str


class UserProfile(BaseModel):
    """Complete user profile"""
    user_name: Optional[str] = None
    answers: list[ProfileAnswer] = []
    onboarding_started: Optional[datetime] = None
    onboarding_completed: bool = False
    last_updated: Optional[datetime] = None


# ============== PROFILE QUESTIONS ==============
# Organized by category with priority (lower = earlier in onboarding)

PROFILE_QUESTIONS = [
    # TIER 1: Foundation (Priority 1-2)
    ProfileQuestion(
        id="name",
        category="foundation",
        question="What would you like me to call you? Do you have a preferred name or nickname?",
        priority=1
    ),
    ProfileQuestion(
        id="goals_for_gala",
        category="foundation",
        question="What are you hoping I can help you with? What made you want a personal AI assistant?",
        priority=1
    ),
    ProfileQuestion(
        id="communication_style",
        category="foundation",
        question="How do you prefer to receive information and feedback? Do you like me to be direct and blunt, or more gentle and diplomatic?",
        priority=2
    ),
    ProfileQuestion(
        id="life_stage",
        category="foundation",
        question="Tell me a bit about where you are in life right now. Your general age range, whether you're working, retired, studying, or something else entirely.",
        priority=2
    ),
    
    # TIER 2: Values & Identity (Priority 3)
    ProfileQuestion(
        id="core_values",
        category="values",
        question="What values are most important to you? What principles guide your decisions and how you want to live?",
        priority=3
    ),
    ProfileQuestion(
        id="beliefs_success",
        category="values",
        question="How do you define success for yourself? What does a life well-lived look like to you?",
        priority=3
    ),
    ProfileQuestion(
        id="worldview",
        category="values",
        question="How would you describe your general worldview or philosophy? This helps me understand where you're coming from on various topics.",
        follow_up="Feel free to share political, spiritual, or philosophical leanings if you're comfortable - I won't judge, I just want to understand you better.",
        priority=3
    ),
    ProfileQuestion(
        id="dealbreakers",
        category="values",
        question="What are your non-negotiables? Things you absolutely won't compromise on, whether in relationships, work, or life in general?",
        priority=3
    ),
    
    # TIER 3: Personality & Style (Priority 4)
    ProfileQuestion(
        id="decision_style",
        category="personality",
        question="How do you typically make decisions? Are you more analytical and methodical, or do you trust your gut and intuition?",
        priority=4
    ),
    ProfileQuestion(
        id="risk_tolerance",
        category="personality",
        question="How do you feel about risk and uncertainty? Are you someone who plays it safe, or do you embrace calculated risks?",
        priority=4
    ),
    ProfileQuestion(
        id="feedback_preference",
        category="personality",
        question="When I need to tell you something you might not want to hear, how should I approach it? Some people want it straight, others prefer a softer touch.",
        priority=4
    ),
    ProfileQuestion(
        id="energy_patterns",
        category="personality",
        question="Are you a morning person or night owl? When do you feel most energized and focused?",
        priority=4
    ),
    
    # TIER 4: Relationships & Social (Priority 5)
    ProfileQuestion(
        id="important_people",
        category="relationships",
        question="Who are the most important people in your life? Tell me about your family, close friends, or significant relationships.",
        priority=5
    ),
    ProfileQuestion(
        id="social_style",
        category="relationships",
        question="Would you describe yourself as more introverted or extroverted? How do you prefer to spend your social energy?",
        priority=5
    ),
    ProfileQuestion(
        id="relationship_goals",
        category="relationships",
        question="Are there any relationship goals or challenges you're working on? This could be romantic, family, friendships, or professional relationships.",
        priority=5
    ),
    
    # TIER 5: Professional Life (Priority 6)
    ProfileQuestion(
        id="occupation",
        category="professional",
        question="What do you do for work? Or if you're not working traditionally, how do you spend most of your productive time?",
        priority=6
    ),
    ProfileQuestion(
        id="career_goals",
        category="professional",
        question="What are your professional or career goals? Where do you want to be in the next few years?",
        priority=6
    ),
    ProfileQuestion(
        id="professional_strengths",
        category="professional",
        question="What skills or abilities are you most proud of? What do you bring to the table that others don't?",
        priority=6
    ),
    ProfileQuestion(
        id="professional_challenges",
        category="professional",
        question="What professional challenges or frustrations are you dealing with? What obstacles are in your way?",
        priority=6
    ),
    
    # TIER 6: Personal Life & Wellness (Priority 7)
    ProfileQuestion(
        id="hobbies",
        category="personal",
        question="What do you do for fun? What hobbies or activities bring you joy outside of work?",
        priority=7
    ),
    ProfileQuestion(
        id="health_considerations",
        category="personal",
        question="Is there anything about your physical or mental health I should know about? This helps me give you better advice and be more understanding.",
        follow_up="Only share what you're comfortable with - this is just to help me support you better.",
        priority=7
    ),
    ProfileQuestion(
        id="stress_triggers",
        category="personal",
        question="What tends to stress you out? What situations or things reliably put you in a bad headspace?",
        priority=7
    ),
    ProfileQuestion(
        id="recharge_methods",
        category="personal",
        question="How do you recharge and take care of yourself? What helps you feel better when you're drained or overwhelmed?",
        priority=7
    ),
    
    # TIER 7: Goals & Aspirations (Priority 8)
    ProfileQuestion(
        id="short_term_goals",
        category="goals",
        question="What are you trying to accomplish in the next few months? Any specific goals or projects you're focused on?",
        priority=8
    ),
    ProfileQuestion(
        id="long_term_vision",
        category="goals",
        question="Where do you see yourself in five or ten years? What's your longer-term vision for your life?",
        priority=8
    ),
    ProfileQuestion(
        id="dreams",
        category="goals",
        question="What are your dreams - the 'someday' aspirations that might seem far off but matter to you?",
        priority=8
    ),
    ProfileQuestion(
        id="bucket_list",
        category="goals",
        question="If you have a bucket list, what's on it? Things you want to experience, accomplish, or try before you're done?",
        priority=8
    ),
    
    # TIER 8: Fears & Shadows (Priority 9)
    ProfileQuestion(
        id="worries",
        category="fears",
        question="What keeps you up at night? What worries or anxieties do you find yourself returning to?",
        priority=9
    ),
    ProfileQuestion(
        id="past_experiences",
        category="fears",
        question="Are there past experiences - good or bad - that significantly shaped who you are today?",
        follow_up="You don't have to go into detail, just knowing these exist helps me understand you better.",
        priority=9
    ),
    ProfileQuestion(
        id="avoidances",
        category="fears",
        question="What do you tend to avoid? Whether it's conversations, situations, or activities - what makes you uncomfortable?",
        priority=9
    ),
    ProfileQuestion(
        id="regrets",
        category="fears",
        question="Do you have any regrets or unfinished business that weighs on you? Things you wish you'd done differently?",
        priority=9
    ),
    
    # TIER 9: Preferences & Misc (Priority 10)
    ProfileQuestion(
        id="pet_peeves",
        category="preferences",
        question="What are your pet peeves? Things that annoy you or rub you the wrong way?",
        priority=10
    ),
    ProfileQuestion(
        id="things_you_love",
        category="preferences",
        question="What do you absolutely love? Things that reliably make you happy or excited?",
        priority=10
    ),
    ProfileQuestion(
        id="learning_interests",
        category="preferences",
        question="What topics or subjects are you curious about? What would you like to learn more about?",
        priority=10
    ),
    ProfileQuestion(
        id="anything_else",
        category="preferences",
        question="Is there anything else important about you that I should know? Anything we haven't covered that would help me understand and serve you better?",
        priority=10
    ),
]


class UserProfileService:
    """Manages user profile data and onboarding process"""
    
    def __init__(self, data_dir: Path = Path("./data")):
        self.data_dir = data_dir
        self.profile_file = data_dir / "user_profile.json"
        self.questions = sorted(PROFILE_QUESTIONS, key=lambda q: q.priority)
        self._profile: Optional[UserProfile] = None
    
    def _ensure_dir(self):
        """Ensure data directory exists"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def load_profile(self) -> UserProfile:
        """Load user profile from disk"""
        if self._profile is not None:
            return self._profile
            
        self._ensure_dir()
        
        if self.profile_file.exists():
            try:
                data = json.loads(self.profile_file.read_text(encoding='utf-8'))
                self._profile = UserProfile(**data)
            except Exception as e:
                print(f"Error loading profile: {e}")
                self._profile = UserProfile()
        else:
            self._profile = UserProfile()
        
        return self._profile
    
    def save_profile(self, profile: Optional[UserProfile] = None) -> UserProfile:
        """Save user profile to disk"""
        self._ensure_dir()
        
        if profile:
            self._profile = profile
        
        if self._profile is None:
            self._profile = UserProfile()
        
        self._profile.last_updated = datetime.now()
        
        # Convert to dict with datetime serialization
        data = self._profile.model_dump()
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        for answer in data.get('answers', []):
            if isinstance(answer.get('answered_at'), datetime):
                answer['answered_at'] = answer['answered_at'].isoformat()
        
        self.profile_file.write_text(
            json.dumps(data, indent=2, default=str),
            encoding='utf-8'
        )
        
        return self._profile
    
    def get_answered_question_ids(self) -> set[str]:
        """Get IDs of questions that have been answered"""
        profile = self.load_profile()
        return {a.question_id for a in profile.answers}
    
    def get_unanswered_questions(self) -> list[ProfileQuestion]:
        """Get questions that haven't been answered yet"""
        answered_ids = self.get_answered_question_ids()
        return [q for q in self.questions if q.id not in answered_ids]
    
    def get_next_questions(self, count: int = 1) -> list[ProfileQuestion]:
        """Get the next N questions to ask (by priority)"""
        unanswered = self.get_unanswered_questions()
        return unanswered[:count]
    
    def get_questions_by_category(self, category: str) -> list[ProfileQuestion]:
        """Get all questions in a category"""
        return [q for q in self.questions if q.category == category]
    
    def get_categories(self) -> list[str]:
        """Get list of all categories"""
        return list(dict.fromkeys(q.category for q in self.questions))
    
    def get_progress(self) -> dict:
        """Get onboarding progress stats"""
        total = len(self.questions)
        answered = len(self.get_answered_question_ids())
        
        # Progress by category
        categories = {}
        for cat in self.get_categories():
            cat_questions = self.get_questions_by_category(cat)
            cat_answered = len([q for q in cat_questions if q.id in self.get_answered_question_ids()])
            categories[cat] = {
                "total": len(cat_questions),
                "answered": cat_answered,
                "complete": cat_answered == len(cat_questions)
            }
        
        return {
            "total_questions": total,
            "answered": answered,
            "remaining": total - answered,
            "percent_complete": round((answered / total) * 100, 1) if total > 0 else 0,
            "categories": categories,
            "is_complete": answered >= total
        }
    
    def record_answer(self, question_id: str, answer: str) -> ProfileAnswer:
        """Record an answer to a profile question"""
        profile = self.load_profile()
        
        # Find the question
        question = next((q for q in self.questions if q.id == question_id), None)
        if not question:
            raise ValueError(f"Unknown question ID: {question_id}")
        
        # Check if already answered, update if so
        existing = next((a for a in profile.answers if a.question_id == question_id), None)
        if existing:
            profile.answers.remove(existing)
        
        # Create new answer
        profile_answer = ProfileAnswer(
            question_id=question_id,
            question=question.question,
            answer=answer,
            answered_at=datetime.now(),
            category=question.category
        )
        
        profile.answers.append(profile_answer)
        
        # Update onboarding status
        if not profile.onboarding_started:
            profile.onboarding_started = datetime.now()
        
        if len(self.get_unanswered_questions()) == 0:
            profile.onboarding_completed = True
        
        # Handle special questions
        if question_id == "name" and answer:
            profile.user_name = answer
        
        self.save_profile(profile)
        return profile_answer
    
    def get_profile_summary(self) -> str:
        """Generate a text summary of the user profile for the system prompt"""
        profile = self.load_profile()
        
        if not profile.answers:
            return ""
        
        # Group answers by category
        by_category = {}
        for answer in profile.answers:
            if answer.category not in by_category:
                by_category[answer.category] = []
            by_category[answer.category].append(answer)
        
        # Build summary
        lines = []
        
        if profile.user_name:
            lines.append(f"Name: {profile.user_name}")
        
        # Category display names
        category_names = {
            "foundation": "Background",
            "values": "Values & Beliefs",
            "personality": "Personality",
            "relationships": "Relationships",
            "professional": "Professional Life",
            "personal": "Personal Life",
            "goals": "Goals & Aspirations",
            "fears": "Concerns & Challenges",
            "preferences": "Preferences"
        }
        
        for category in ["foundation", "values", "personality", "relationships", 
                         "professional", "personal", "goals", "fears", "preferences"]:
            if category in by_category:
                cat_name = category_names.get(category, category.title())
                lines.append(f"\n{cat_name}:")
                for answer in by_category[category]:
                    # Truncate very long answers
                    answer_text = answer.answer
                    if len(answer_text) > 300:
                        answer_text = answer_text[:300] + "..."
                    lines.append(f"- {answer_text}")
        
        return "\n".join(lines)
    
    def clear_profile(self) -> None:
        """Clear the entire profile (start fresh)"""
        self._profile = UserProfile()
        self.save_profile()
    
    def delete_answer(self, question_id: str) -> bool:
        """Delete a specific answer"""
        profile = self.load_profile()
        
        original_count = len(profile.answers)
        profile.answers = [a for a in profile.answers if a.question_id != question_id]
        
        if len(profile.answers) < original_count:
            profile.onboarding_completed = False
            self.save_profile(profile)
            return True
        
        return False


# Singleton instance
user_profile_service = UserProfileService()

