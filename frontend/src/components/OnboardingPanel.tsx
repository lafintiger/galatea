import { useState, useEffect, useCallback } from 'react';

interface ProfileQuestion {
  id: string;
  category: string;
  question: string;
  follow_up?: string;
  priority: number;
}

interface ProfileAnswer {
  question_id: string;
  question: string;
  answer: string;
  category: string;
  answered_at: string;
}

interface Progress {
  total_questions: number;
  answered: number;
  remaining: number;
  percent_complete: number;
  categories: Record<string, { total: number; answered: number; complete: boolean }>;
  is_complete: boolean;
}

interface OnboardingPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  foundation: '🏠 Foundation',
  values: '💎 Values & Beliefs',
  personality: '🎭 Personality',
  relationships: '👥 Relationships',
  professional: '💼 Professional',
  personal: '🌱 Personal Life',
  goals: '🎯 Goals & Dreams',
  fears: '🌙 Concerns & Shadows',
  preferences: '⭐ Preferences',
};

export function OnboardingPanel({ isOpen, onClose }: OnboardingPanelProps) {
  const [currentQuestion, setCurrentQuestion] = useState<ProfileQuestion | null>(null);
  const [answer, setAnswer] = useState('');
  const [progress, setProgress] = useState<Progress | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState<'guided' | 'browse'>('guided');
  const [allAnswers, setAllAnswers] = useState<ProfileAnswer[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [categoryQuestions, setCategoryQuestions] = useState<ProfileQuestion[]>([]);
  const [editingAnswer, setEditingAnswer] = useState<string | null>(null);
  const [editText, setEditText] = useState('');

  const fetchProgress = useCallback(async () => {
    try {
      const res = await fetch('/api/profile');
      const data = await res.json();
      setProgress(data.progress);
      setAllAnswers(data.profile.answers || []);
    } catch (err) {
      console.error('Failed to fetch profile:', err);
    }
  }, []);

  const fetchNextQuestion = useCallback(async () => {
    try {
      const res = await fetch('/api/profile/next');
      const data = await res.json();
      if (data.questions && data.questions.length > 0) {
        setCurrentQuestion(data.questions[0]);
      } else {
        setCurrentQuestion(null);
      }
      setProgress(data.progress);
    } catch (err) {
      console.error('Failed to fetch next question:', err);
    }
  }, []);

  const fetchCategoryQuestions = useCallback(async (category: string) => {
    try {
      const res = await fetch(`/api/profile/questions?category=${category}`);
      const data = await res.json();
      setCategoryQuestions(data.questions || []);
    } catch (err) {
      console.error('Failed to fetch category questions:', err);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchProgress();
      fetchNextQuestion();
    }
  }, [isOpen, fetchProgress, fetchNextQuestion]);

  useEffect(() => {
    if (selectedCategory) {
      fetchCategoryQuestions(selectedCategory);
    }
  }, [selectedCategory, fetchCategoryQuestions]);

  const handleSubmitAnswer = async () => {
    if (!currentQuestion || !answer.trim()) return;

    setIsLoading(true);
    try {
      const res = await fetch('/api/profile/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_id: currentQuestion.id,
          answer: answer.trim(),
        }),
      });
      
      const data = await res.json();
      if (data.success) {
        setAnswer('');
        setProgress(data.progress);
        if (data.next_question) {
          setCurrentQuestion(data.next_question);
        } else {
          setCurrentQuestion(null);
        }
        // Refresh answers list
        fetchProgress();
      }
    } catch (err) {
      console.error('Failed to submit answer:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpdateAnswer = async (questionId: string, newAnswer: string) => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/profile/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_id: questionId,
          answer: newAnswer.trim(),
        }),
      });
      
      if (res.ok) {
        setEditingAnswer(null);
        setEditText('');
        fetchProgress();
      }
    } catch (err) {
      console.error('Failed to update answer:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteAnswer = async (questionId: string) => {
    if (!confirm('Are you sure you want to delete this answer?')) return;
    
    try {
      const res = await fetch(`/api/profile/answer/${questionId}`, {
        method: 'DELETE',
      });
      
      if (res.ok) {
        fetchProgress();
        fetchNextQuestion();
      }
    } catch (err) {
      console.error('Failed to delete answer:', err);
    }
  };

  const handleSkip = () => {
    fetchNextQuestion();
    setAnswer('');
  };

  const startEditing = (answer: ProfileAnswer) => {
    setEditingAnswer(answer.question_id);
    setEditText(answer.answer);
  };

  if (!isOpen) return null;

  const answeredIds = new Set(allAnswers.map(a => a.question_id));

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-cyan-500/30 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-cyan-500/20 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-cyan-400">Get to Know You</h2>
            <p className="text-sm text-gray-400 mt-1">
              Help Gala understand you better for more personalized assistance
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Progress Bar */}
        {progress && (
          <div className="px-4 py-3 border-b border-cyan-500/10 bg-gray-800/50">
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-gray-400">
                {progress.answered} of {progress.total_questions} questions answered
              </span>
              <span className="text-cyan-400 font-medium">
                {progress.percent_complete}%
              </span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div
                className="bg-gradient-to-r from-cyan-500 to-blue-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${progress.percent_complete}%` }}
              />
            </div>
          </div>
        )}

        {/* Mode Toggle */}
        <div className="px-4 py-2 border-b border-cyan-500/10 flex gap-2">
          <button
            onClick={() => setMode('guided')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              mode === 'guided'
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            🎯 Guided
          </button>
          <button
            onClick={() => setMode('browse')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              mode === 'browse'
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            📋 Browse & Edit
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {mode === 'guided' ? (
            // Guided Mode - One question at a time
            <div className="space-y-4">
              {progress?.is_complete ? (
                <div className="text-center py-8">
                  <div className="text-4xl mb-4">🎉</div>
                  <h3 className="text-xl font-bold text-cyan-400 mb-2">
                    Onboarding Complete!
                  </h3>
                  <p className="text-gray-400">
                    Gala now has a comprehensive understanding of who you are.
                    You can always update your answers in Browse mode.
                  </p>
                </div>
              ) : currentQuestion ? (
                <>
                  <div className="text-sm text-cyan-400/70 font-medium uppercase tracking-wider">
                    {CATEGORY_LABELS[currentQuestion.category] || currentQuestion.category}
                  </div>
                  
                  <div className="text-lg text-white leading-relaxed">
                    {currentQuestion.question}
                  </div>
                  
                  {currentQuestion.follow_up && (
                    <div className="text-sm text-gray-400 italic">
                      {currentQuestion.follow_up}
                    </div>
                  )}
                  
                  <textarea
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    placeholder="Share your thoughts..."
                    className="w-full h-32 bg-gray-800 border border-gray-700 rounded-lg p-3 text-white placeholder-gray-500 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 outline-none resize-none"
                    disabled={isLoading}
                  />
                  
                  <div className="flex gap-3">
                    <button
                      onClick={handleSubmitAnswer}
                      disabled={!answer.trim() || isLoading}
                      className="flex-1 bg-gradient-to-r from-cyan-500 to-blue-500 text-white font-medium py-2 px-4 rounded-lg hover:from-cyan-400 hover:to-blue-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                    >
                      {isLoading ? 'Saving...' : 'Save & Continue'}
                    </button>
                    <button
                      onClick={handleSkip}
                      disabled={isLoading}
                      className="px-4 py-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
                    >
                      Skip for now
                    </button>
                  </div>
                </>
              ) : (
                <div className="text-center py-8 text-gray-400">
                  Loading questions...
                </div>
              )}
            </div>
          ) : (
            // Browse Mode - View/edit all answers by category
            <div className="space-y-4">
              {/* Category Pills */}
              <div className="flex flex-wrap gap-2">
                {progress && Object.entries(progress.categories).map(([cat, info]) => (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(selectedCategory === cat ? null : cat)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
                      selectedCategory === cat
                        ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                        : info.complete
                        ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                        : 'bg-gray-800 text-gray-400 border border-gray-700 hover:border-gray-600'
                    }`}
                  >
                    {CATEGORY_LABELS[cat] || cat}
                    <span className="ml-2 text-xs opacity-70">
                      {info.answered}/{info.total}
                    </span>
                  </button>
                ))}
              </div>

              {/* Questions/Answers for selected category */}
              {selectedCategory && (
                <div className="space-y-3 mt-4">
                  {categoryQuestions.map((q) => {
                    const existingAnswer = allAnswers.find(a => a.question_id === q.id);
                    const isEditing = editingAnswer === q.id;
                    
                    return (
                      <div
                        key={q.id}
                        className={`p-4 rounded-lg border ${
                          existingAnswer
                            ? 'bg-gray-800/50 border-gray-700'
                            : 'bg-gray-800/30 border-gray-700/50 border-dashed'
                        }`}
                      >
                        <div className="text-sm text-white mb-2">{q.question}</div>
                        
                        {isEditing ? (
                          <div className="space-y-2">
                            <textarea
                              value={editText}
                              onChange={(e) => setEditText(e.target.value)}
                              className="w-full h-24 bg-gray-900 border border-gray-600 rounded p-2 text-white text-sm focus:border-cyan-500 outline-none resize-none"
                            />
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleUpdateAnswer(q.id, editText)}
                                disabled={isLoading}
                                className="px-3 py-1 bg-cyan-500/20 text-cyan-400 text-sm rounded hover:bg-cyan-500/30 transition-colors"
                              >
                                Save
                              </button>
                              <button
                                onClick={() => setEditingAnswer(null)}
                                className="px-3 py-1 text-gray-400 text-sm hover:text-white transition-colors"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : existingAnswer ? (
                          <div>
                            <div className="text-gray-300 text-sm bg-gray-900/50 rounded p-2 mb-2">
                              {existingAnswer.answer}
                            </div>
                            <div className="flex gap-2">
                              <button
                                onClick={() => startEditing(existingAnswer)}
                                className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDeleteAnswer(q.id)}
                                className="text-xs text-red-400 hover:text-red-300 transition-colors"
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button
                            onClick={() => {
                              setCurrentQuestion(q);
                              setMode('guided');
                            }}
                            className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
                          >
                            + Answer this question
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {!selectedCategory && (
                <div className="text-center py-8 text-gray-400">
                  Select a category above to view and edit answers
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-cyan-500/20 bg-gray-800/50">
          <p className="text-xs text-gray-500 text-center">
            Your answers help Gala provide more personalized and relevant assistance.
            All information is stored locally and never shared.
          </p>
        </div>
      </div>
    </div>
  );
}

