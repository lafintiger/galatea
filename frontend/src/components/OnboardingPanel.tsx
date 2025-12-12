import { useState, useEffect, useCallback, useRef } from 'react';

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

interface EnrolledFace {
  id: string;
  name: string;
  role: string;
  enrolled_at: string;
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
  const [mode, setMode] = useState<'guided' | 'browse' | 'faces'>('guided');
  const [allAnswers, setAllAnswers] = useState<ProfileAnswer[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [categoryQuestions, setCategoryQuestions] = useState<ProfileQuestion[]>([]);
  const [editingAnswer, setEditingAnswer] = useState<string | null>(null);
  const [editText, setEditText] = useState('');
  
  // Face enrollment state
  const [enrolledFaces, setEnrolledFaces] = useState<EnrolledFace[]>([]);
  const [ownerEnrolled, setOwnerEnrolled] = useState(false);
  const [ownerName, setOwnerName] = useState<string | null>(null);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [enrollName, setEnrollName] = useState('');
  const [enrollRole, setEnrollRole] = useState<'owner' | 'friend' | 'family'>('owner');
  const [enrollMessage, setEnrollMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [visionAvailable, setVisionAvailable] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

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

  const checkVisionHealth = useCallback(async () => {
    try {
      const res = await fetch('/api/vision/live/health');
      const data = await res.json();
      setVisionAvailable(data.available);
    } catch {
      setVisionAvailable(false);
    }
  }, []);

  const fetchFaces = useCallback(async () => {
    try {
      const res = await fetch('/api/faces');
      const data = await res.json();
      setEnrolledFaces(data.faces || []);
      setOwnerEnrolled(data.owner_enrolled || false);
      setOwnerName(data.owner_name || null);
    } catch (err) {
      console.error('Failed to fetch faces:', err);
    }
  }, []);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: 'user', width: 640, height: 480 } 
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsCapturing(true);
    } catch (err) {
      console.error('Failed to access camera:', err);
      setEnrollMessage({ type: 'error', text: 'Could not access camera. Please check permissions.' });
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    setIsCapturing(false);
  };

  const captureFrame = () => {
    if (!videoRef.current) return;
    
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth || 640;
    canvas.height = videoRef.current.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(videoRef.current, 0, 0);
      const imageData = canvas.toDataURL('image/jpeg', 0.9);
      // Remove the data:image/jpeg;base64, prefix
      const base64 = imageData.split(',')[1];
      setCapturedImage(base64);
      stopCamera();
    }
  };

  const enrollFace = async () => {
    if (!enrollName.trim()) {
      setEnrollMessage({ type: 'error', text: 'Please enter a name' });
      return;
    }

    setIsLoading(true);
    setEnrollMessage(null);
    
    try {
      const res = await fetch('/api/faces/enroll', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: enrollName.trim(),
          role: enrollRole,
          image: capturedImage,
        }),
      });
      
      const data = await res.json();
      
      if (data.success) {
        setEnrollMessage({ type: 'success', text: data.message });
        setCapturedImage(null);
        setEnrollName('');
        fetchFaces();
      } else {
        setEnrollMessage({ type: 'error', text: data.message || 'Enrollment failed' });
      }
    } catch (err) {
      console.error('Enrollment error:', err);
      setEnrollMessage({ type: 'error', text: 'Failed to enroll face' });
    } finally {
      setIsLoading(false);
    }
  };

  const deleteFace = async (faceId: string) => {
    if (!confirm('Are you sure you want to remove this person?')) return;
    
    try {
      const res = await fetch(`/api/faces/${faceId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchFaces();
        setEnrollMessage({ type: 'success', text: 'Face removed successfully' });
      }
    } catch (err) {
      console.error('Delete error:', err);
      setEnrollMessage({ type: 'error', text: 'Failed to remove face' });
    }
  };

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
      checkVisionHealth();
      fetchFaces();
    } else {
      // Clean up camera when panel closes
      stopCamera();
    }
  }, [isOpen, fetchProgress, fetchNextQuestion, checkVisionHealth, fetchFaces]);

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
          <button
            onClick={() => { setMode('faces'); stopCamera(); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              mode === 'faces'
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                : 'text-gray-400 hover:text-white hover:bg-gray-800'
            }`}
          >
            👤 Face ID {ownerEnrolled && '✓'}
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
          ) : mode === 'browse' ? (
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
          ) : (
            // Faces Mode - Face Recognition Setup
            <div className="space-y-4">
              {!visionAvailable ? (
                <div className="text-center py-8">
                  <div className="text-4xl mb-4">👁️</div>
                  <h3 className="text-lg font-bold text-yellow-400 mb-2">
                    Vision Service Not Available
                  </h3>
                  <p className="text-gray-400 text-sm">
                    Face recognition requires the Galatea Vision service to be running.
                    <br />
                    Start it with: <code className="text-cyan-400">vision/start_native.bat</code>
                  </p>
                </div>
              ) : (
                <>
                  {/* Owner Status */}
                  <div className={`p-4 rounded-lg border ${ownerEnrolled ? 'bg-green-500/10 border-green-500/30' : 'bg-yellow-500/10 border-yellow-500/30'}`}>
                    <div className="flex items-center gap-3">
                      <div className={`text-2xl ${ownerEnrolled ? 'text-green-400' : 'text-yellow-400'}`}>
                        {ownerEnrolled ? '✅' : '⚠️'}
                      </div>
                      <div>
                        <div className={`font-medium ${ownerEnrolled ? 'text-green-400' : 'text-yellow-400'}`}>
                          {ownerEnrolled ? `Owner: ${ownerName}` : 'Owner Not Enrolled'}
                        </div>
                        <div className="text-sm text-gray-400">
                          {ownerEnrolled 
                            ? 'Gala will recognize you and keep your conversations private' 
                            : 'Enroll your face so Gala knows who you are'}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Enrollment UI */}
                  <div className="p-4 rounded-lg border border-gray-700 bg-gray-800/50">
                    <h4 className="font-medium text-white mb-4">
                      {ownerEnrolled ? 'Add a Friend or Family Member' : 'Enroll Your Face (Owner)'}
                    </h4>
                    
                    {/* Message */}
                    {enrollMessage && (
                      <div className={`p-3 rounded-lg mb-4 ${
                        enrollMessage.type === 'success' 
                          ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                          : 'bg-red-500/20 text-red-400 border border-red-500/30'
                      }`}>
                        {enrollMessage.text}
                      </div>
                    )}

                    {/* Camera / Captured Image */}
                    <div className="mb-4">
                      {isCapturing ? (
                        <div className="relative">
                          <video 
                            ref={videoRef} 
                            autoPlay 
                            playsInline 
                            muted 
                            className="w-full rounded-lg bg-black"
                          />
                          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2">
                            <button
                              onClick={captureFrame}
                              className="px-4 py-2 bg-cyan-500 text-white rounded-lg font-medium hover:bg-cyan-400 transition-colors"
                            >
                              📸 Capture
                            </button>
                            <button
                              onClick={stopCamera}
                              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-500 transition-colors"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      ) : capturedImage ? (
                        <div className="relative">
                          <img 
                            src={`data:image/jpeg;base64,${capturedImage}`} 
                            alt="Captured" 
                            className="w-full rounded-lg"
                          />
                          <button
                            onClick={() => { setCapturedImage(null); startCamera(); }}
                            className="absolute top-2 right-2 px-3 py-1 bg-gray-800/80 text-white text-sm rounded hover:bg-gray-700 transition-colors"
                          >
                            Retake
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={startCamera}
                          className="w-full h-48 border-2 border-dashed border-gray-600 rounded-lg flex flex-col items-center justify-center gap-2 hover:border-cyan-500 hover:bg-cyan-500/5 transition-colors"
                        >
                          <div className="text-4xl">📷</div>
                          <div className="text-gray-400">Click to start camera</div>
                        </button>
                      )}
                    </div>

                    {/* Name and Role */}
                    {capturedImage && (
                      <div className="space-y-3">
                        <input
                          type="text"
                          value={enrollName}
                          onChange={(e) => setEnrollName(e.target.value)}
                          placeholder="Enter name..."
                          className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:border-cyan-500 outline-none"
                        />
                        
                        {ownerEnrolled && (
                          <div className="flex gap-2">
                            <button
                              onClick={() => setEnrollRole('friend')}
                              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                                enrollRole === 'friend'
                                  ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                                  : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                              }`}
                            >
                              👋 Friend
                            </button>
                            <button
                              onClick={() => setEnrollRole('family')}
                              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                                enrollRole === 'family'
                                  ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                                  : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
                              }`}
                            >
                              👨‍👩‍👧 Family
                            </button>
                          </div>
                        )}
                        
                        <button
                          onClick={enrollFace}
                          disabled={isLoading || !enrollName.trim()}
                          className="w-full py-2 bg-gradient-to-r from-cyan-500 to-blue-500 text-white font-medium rounded-lg hover:from-cyan-400 hover:to-blue-400 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                        >
                          {isLoading ? 'Enrolling...' : ownerEnrolled ? 'Add Person' : 'Enroll as Owner'}
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Enrolled Faces List */}
                  {enrolledFaces.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="font-medium text-white">Enrolled People</h4>
                      {enrolledFaces.map((face) => (
                        <div 
                          key={face.id}
                          className="flex items-center justify-between p-3 rounded-lg bg-gray-800/50 border border-gray-700"
                        >
                          <div className="flex items-center gap-3">
                            <div className={`text-xl ${
                              face.role === 'owner' ? 'text-green-400' : 
                              face.role === 'family' ? 'text-purple-400' : 'text-blue-400'
                            }`}>
                              {face.role === 'owner' ? '👑' : face.role === 'family' ? '👨‍👩‍👧' : '👋'}
                            </div>
                            <div>
                              <div className="text-white font-medium">{face.name}</div>
                              <div className="text-xs text-gray-400 capitalize">{face.role}</div>
                            </div>
                          </div>
                          <button
                            onClick={() => deleteFace(face.id)}
                            className="p-2 text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded transition-colors"
                            title="Remove"
                          >
                            🗑️
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Privacy Info */}
                  <div className="p-3 rounded-lg bg-gray-800/30 border border-gray-700/50">
                    <div className="text-sm text-gray-400">
                      <strong className="text-cyan-400">🔒 Privacy:</strong> Face data is stored locally and never leaves your computer. 
                      When face recognition is active:
                      <ul className="mt-2 ml-4 list-disc space-y-1">
                        <li><strong>Owner:</strong> Full access to conversations and personal context</li>
                        <li><strong>Friends/Family:</strong> Can chat, but won't see your personal info</li>
                        <li><strong>Unknown:</strong> Gala will politely decline to have a conversation</li>
                      </ul>
                    </div>
                  </div>
                </>
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



