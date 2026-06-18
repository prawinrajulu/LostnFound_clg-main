import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { verificationAPI } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { Shield, ArrowLeft, RefreshCw, Send, CheckCircle, XCircle, MapPin, Calendar, CheckSquare } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const AdminVerificationSession = () => {
  const { matchId } = useParams();
  const navigate = useNavigate();
  const [sessionData, setSessionData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Inputs
  const [questionText, setQuestionText] = useState('');
  const [notesText, setNotesText] = useState('');
  const [handoverChecked, setHandoverChecked] = useState(false);
  
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    fetchSession();
  }, [matchId]);

  const fetchSession = async () => {
    setLoading(true);
    try {
      const response = await verificationAPI.getSession(matchId);
      setSessionData(response.data);
      setNotesText(response.data.session?.admin_notes || '');
      setHandoverChecked(response.data.session?.handover_confirmed || false);
    } catch (error) {
      console.error('Failed to fetch session:', error);
      toast.error('Failed to load verification session');
    } finally {
      setLoading(false);
    }
  };

  const handleAddQuestion = async () => {
    if (!questionText.trim()) return;
    setSubmitting(true);
    try {
      await verificationAPI.addQuestion(matchId, questionText.trim());
      toast.success('Question sent to student!');
      setQuestionText('');
      fetchSession();
    } catch (error) {
      toast.error('Failed to send question');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSaveNotes = async () => {
    try {
      await verificationAPI.updateNotes(matchId, notesText);
      toast.success('Notes saved');
    } catch (error) {
      toast.error('Failed to save notes');
    }
  };

  const handleDecision = async (status) => {
    try {
      await verificationAPI.makeDecision(matchId, status);
      toast.success(`Verification ${status}`);
      fetchSession();
    } catch (error) {
      toast.error('Failed to set decision');
    }
  };

  const handleComplete = async () => {
    try {
      await verificationAPI.completeVerification(matchId, handoverChecked);
      toast.success('Item successfully returned and match completed!');
      navigate('/admin/verification-queue');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to complete match');
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-24">
        <div className="spinner mb-4" />
        <p className="text-slate-500 font-medium">Loading session...</p>
      </div>
    );
  }

  if (!sessionData) {
    return (
      <div className="text-center py-24">
        <p className="text-slate-500">Session not found.</p>
        <Button onClick={() => navigate('/admin/verification-queue')} className="mt-4">
          Return to Queue
        </Button>
      </div>
    );
  }

  const { match, session, questions } = sessionData;
  
  // Validation logic
  const hasQuestions = questions && questions.length > 0;
  const allAnswered = hasQuestions && questions.every(q => q.answer);
  const isApproved = match.status === 'approved' || match.status === 'completed';
  const canComplete = hasQuestions && allAnswered && isApproved && handoverChecked && match.status !== 'completed';

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'student_notified': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'verification_started': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'qa_completed': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'approved': return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'rejected': return 'bg-rose-100 text-rose-800 border-rose-200';
      case 'completed': return 'bg-slate-100 text-slate-800 border-slate-200';
      default: return 'bg-slate-100 text-slate-800';
    }
  };

  return (
    <div className="space-y-6 animate-fade-in" data-testid="admin-verification-session">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate('/admin/verification-queue')}>
            <ArrowLeft className="w-5 h-5 text-slate-600" />
          </Button>
          <div>
            <h1 className="font-outfit text-2xl font-bold text-slate-900 flex items-center gap-2">
              <Shield className="w-6 h-6 text-emerald-600" />
              Verification Interview
            </h1>
            <p className="text-slate-500 text-sm">Match ID: {matchId}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge className={getStatusColor(match.status)}>
            {match.status.replace('_', ' ')}
          </Badge>
          <Button variant="outline" size="sm" onClick={fetchSession}>
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Comparative Item View (Col 1 & 2) */}
        <div className="lg:col-span-2 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Lost Item */}
            <Card className="border-orange-100 bg-orange-50/20">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <Badge className="status-lost">LOST ITEM</Badge>
                  <span className="text-xs text-slate-500 font-semibold">
                    {match.lost_item?.student?.full_name}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <img
                  src={match.lost_item?.image_url ? `${BACKEND_URL}${match.lost_item.image_url}` : 'https://images.pexels.com/photos/3731256/pexels-photo-3731256.jpeg?auto=compress&cs=tinysrgb&w=100'}
                  alt=""
                  className="w-full h-48 object-cover rounded-lg"
                />
                <h3 className="font-semibold text-slate-800">{match.lost_item?.description}</h3>
                <div className="space-y-1 text-xs text-slate-500">
                  <p className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5" /> {match.lost_item?.location}</p>
                  <p className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> Reported: {match.lost_item?.created_date}</p>
                  <p className="font-medium text-slate-700">Roll: {match.lost_item?.student?.roll_number}</p>
                  <p className="text-slate-600">Dept: {match.lost_item?.student?.department} ({match.lost_item?.student?.year} Yr)</p>
                </div>
              </CardContent>
            </Card>

            {/* Found Item */}
            <Card className="border-emerald-100 bg-emerald-50/20">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <Badge className="status-found">FOUND ITEM</Badge>
                  <span className="text-xs text-slate-500 font-semibold">
                    {match.found_item?.student?.full_name}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <img
                  src={match.found_item?.image_url ? `${BACKEND_URL}${match.found_item.image_url}` : 'https://images.pexels.com/photos/3731256/pexels-photo-3731256.jpeg?auto=compress&cs=tinysrgb&w=100'}
                  alt=""
                  className="w-full h-48 object-cover rounded-lg"
                />
                <h3 className="font-semibold text-slate-800">{match.found_item?.description}</h3>
                <div className="space-y-1 text-xs text-slate-500">
                  <p className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5" /> {match.found_item?.location}</p>
                  <p className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> Reported: {match.found_item?.created_date}</p>
                  <p className="font-medium text-slate-700">Roll: {match.found_item?.student?.roll_number}</p>
                  <p className="text-slate-600">Dept: {match.found_item?.student?.department} ({match.found_item?.student?.year} Yr)</p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Q&A Chat Timeline */}
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="text-lg font-bold font-outfit">Verification Q&A Log</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-4 max-h-[350px] overflow-y-auto pr-2">
                {questions && questions.length === 0 ? (
                  <p className="text-slate-400 text-sm text-center py-6">
                    No questions have been asked yet. Use the input below to start the interview.
                  </p>
                ) : (
                  questions.map((q, idx) => (
                    <div key={q.id} className="space-y-2">
                      {/* Question (Admin) */}
                      <div className="flex justify-end">
                        <div className="bg-slate-100 text-slate-800 rounded-2xl px-4 py-2.5 max-w-[80%] text-sm">
                          <p className="font-semibold text-xs text-slate-500 mb-1">Question {idx + 1}</p>
                          <p>{q.question}</p>
                          <span className="text-[10px] text-slate-400 block mt-1 text-right">
                            {new Date(q.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>
                      
                      {/* Answer (Student) */}
                      <div className="flex justify-start">
                        {q.answer ? (
                          <div className="bg-emerald-50 text-emerald-900 border border-emerald-100 rounded-2xl px-4 py-2.5 max-w-[80%] text-sm">
                            <p className="font-semibold text-xs text-emerald-600 mb-1">Student Answer</p>
                            <p>{q.answer}</p>
                            <span className="text-[10px] text-emerald-500 block mt-1">
                              {new Date(q.answered_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          </div>
                        ) : (
                          <div className="bg-slate-50 text-slate-400 border border-slate-100 rounded-2xl px-4 py-2 text-xs italic">
                            Awaiting response...
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Ask Question Input */}
              {match.status !== 'completed' && (
                <div className="flex gap-2 pt-2 border-t border-slate-100">
                  <textarea
                    placeholder="Ask a verification question (e.g. Describe any internal content, marks, serial numbers...)"
                    value={questionText}
                    onChange={(e) => setQuestionText(e.target.value)}
                    className="flex-1 rounded-lg border border-slate-200 p-2 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400 resize-none h-12"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleAddQuestion();
                      }
                    }}
                  />
                  <Button
                    onClick={handleAddQuestion}
                    disabled={submitting || !questionText.trim()}
                    className="bg-slate-900 hover:bg-slate-800 text-white"
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar Notes & Decision Actions (Col 3) */}
        <div className="space-y-6">
          {/* Admin Notes */}
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="text-lg font-bold font-outfit">Admin Interview Notes</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <textarea
                placeholder="Write observation notes here..."
                value={notesText}
                onChange={(e) => setNotesText(e.target.value)}
                className="w-full h-32 rounded-lg border border-slate-200 p-3 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400 resize-none"
              />
              <Button onClick={handleSaveNotes} size="sm" variant="outline" className="w-full">
                Save Notes
              </Button>
            </CardContent>
          </Card>

          {/* Verification Decision */}
          {match.status !== 'completed' && (
            <Card className="border-slate-200">
              <CardHeader>
                <CardTitle className="text-lg font-bold font-outfit">Review Decision</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex gap-2">
                  <Button
                    onClick={() => handleDecision('approved')}
                    className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
                    variant="default"
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Approve
                  </Button>
                  <Button
                    onClick={() => handleDecision('rejected')}
                    className="flex-1 bg-rose-600 hover:bg-rose-700 text-white"
                    variant="default"
                  >
                    <XCircle className="w-4 h-4 mr-2" />
                    Reject
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Handover & Completion Restriction */}
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle className="text-lg font-bold font-outfit">Release Handover</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Requirements Checklist */}
              <div className="space-y-2 text-xs text-slate-500 bg-slate-50 p-3 rounded-lg border border-slate-100">
                <p className="font-semibold text-slate-700 uppercase tracking-wider mb-2">Completion Requirements</p>
                <div className="flex items-center gap-2">
                  <span className={hasQuestions ? 'text-emerald-500 font-semibold' : 'text-slate-400'}>
                    {hasQuestions ? '✓' : '✗'} At least one question exists
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={allAnswered ? 'text-emerald-500 font-semibold' : 'text-slate-400'}>
                    {allAnswered ? '✓' : '✗'} Student answered all questions
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={isApproved ? 'text-emerald-500 font-semibold' : 'text-slate-400'}>
                    {isApproved ? '✓' : '✗'} Verification status is "Approved"
                  </span>
                </div>
              </div>

              {match.status !== 'completed' ? (
                <>
                  {/* Handover Confirmation Checkbox */}
                  <label className="flex items-start gap-3 cursor-pointer p-3 bg-emerald-50/50 border border-emerald-100 rounded-lg">
                    <input
                      type="checkbox"
                      checked={handoverChecked}
                      onChange={(e) => setHandoverChecked(e.target.checked)}
                      className="mt-0.5 rounded border-emerald-300 text-emerald-600 focus:ring-emerald-500"
                    />
                    <div>
                      <p className="text-sm font-semibold text-emerald-900 leading-none">
                        Item Returned To Owner
                      </p>
                      <p className="text-xs text-emerald-700 mt-1">
                        I confirm the item was physically handed over to the student.
                      </p>
                    </div>
                  </label>

                  <Button
                    onClick={handleComplete}
                    disabled={!canComplete}
                    className="w-full bg-slate-900 hover:bg-slate-800 disabled:bg-slate-200 disabled:text-slate-400 text-white font-medium py-3 h-auto"
                  >
                    <CheckSquare className="w-4 h-4 mr-2" />
                    Complete Match
                  </Button>
                </>
              ) : (
                <div className="bg-slate-100 border border-slate-200 text-slate-700 p-4 rounded-lg text-center text-sm font-medium">
                  ✓ Match Completed & Handed Over
                  {session.completed_at && (
                    <span className="block text-xs text-slate-400 font-normal mt-1">
                      Released: {new Date(session.completed_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default AdminVerificationSession;
