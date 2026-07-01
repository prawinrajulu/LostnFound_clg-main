import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { itemsAPI, claimsAPI, verificationAPI } from '../services/api';
import { ItemGrid } from '../components/ItemCard';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Search, Package, Plus, CheckCircle2, Shield } from 'lucide-react';
import { toast } from 'sonner';

const StudentDashboard = () => {
  const { user } = useAuth();
  const [recentItems, setRecentItems] = useState([]);
  const [myClaims, setMyClaims] = useState([]);
  const [myVerifications, setMyVerifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [itemsRes, claimsRes, verificationsRes] = await Promise.all([
        itemsAPI.getMyItems(),
        claimsAPI.getClaims(),
        verificationAPI.getStudentVerifications()
      ]);
      setRecentItems(itemsRes.data.slice(0, 4));
      setMyClaims(claimsRes.data.slice(0, 3));
      setMyVerifications(verificationsRes.data || []);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async (claimId, answerText) => {
    if (!answerText || !answerText.trim()) {
      toast.error('Please type an answer');
      return;
    }
    try {
      await claimsAPI.answerVerification(claimId, answerText.trim());
      toast.success('Answer submitted successfully!');
      fetchData();
    } catch (error) {
      console.error('Failed to submit answer:', error);
      toast.error('Failed to submit answer');
    }
  };

  const submitVerificationAnswer = async (matchId, questionId, answerText) => {
    if (!answerText || !answerText.trim()) {
      toast.error('Please type an answer');
      return;
    }
    try {
      await verificationAPI.submitAnswer(matchId, questionId, answerText.trim());
      toast.success('Verification answer submitted!');
      fetchData();
    } catch (error) {
      console.error('Failed to submit answer:', error);
      toast.error('Failed to submit answer');
    }
  };

  const getClaimStatusColor = (status) => {
    switch (status) {
      case 'approved': return 'status-found';
      case 'rejected': return 'bg-red-100 text-red-700';
      case 'pending': return 'bg-yellow-100 text-yellow-700';
      case 'under_review': return 'status-claimed';
      default: return 'bg-slate-100 text-slate-600';
    }
  };

  const getMatchStatusColor = (status) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'student_notified':
      case 'verification_started':
      case 'qa_completed':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'approved':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200';
      case 'rejected':
        return 'bg-rose-100 text-rose-800 border-rose-200';
      case 'completed':
        return 'bg-slate-100 text-slate-800 border-slate-200';
      default:
        return 'bg-slate-100 text-slate-600';
    }
  };

  return (
    <div className="space-y-8 animate-fade-in" data-testid="student-dashboard">
      {/* Welcome Section */}
      <div className="bg-white rounded-lg border border-slate-200 p-6">
        <h1 className="font-outfit text-2xl font-bold text-slate-900 mb-2">
          Welcome back, {user?.full_name?.split(' ')[0] || 'Student'}!
        </h1>
        <p className="text-slate-500">
          {user?.department} • {user?.year} Year • {user?.roll_number}
        </p>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link to="/student/report-lost">
          <Card className="card-hover cursor-pointer border-orange-200 bg-orange-50/50">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                  <Search className="w-6 h-6 text-orange-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900">Report Lost Item</h3>
                  <p className="text-sm text-slate-500">Lost something? Report it here</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>

        <Link to="/student/report-found">
          <Card className="card-hover cursor-pointer border-emerald-200 bg-emerald-50/50">
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-emerald-100 rounded-lg flex items-center justify-center">
                  <Package className="w-6 h-6 text-emerald-600" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900">Report Found Item</h3>
                  <p className="text-sm text-slate-500">Found something? Help return it</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Recent Items */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="font-outfit text-xl">My Recent Reports</CardTitle>
          <Link to="/student/my-items">
            <Button variant="outline" size="sm">View All</Button>
          </Link>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="spinner" />
            </div>
          ) : recentItems.length === 0 ? (
            <div className="text-center py-8">
              <Package className="w-12 h-12 mx-auto text-slate-300 mb-3" />
              <p className="text-slate-500">You haven't reported any items yet</p>
              <Link to="/student/report-lost">
                <Button className="mt-4" size="sm">
                  <Plus className="w-4 h-4 mr-2" />
                  Report an Item
                </Button>
              </Link>
            </div>
          ) : (
            <ItemGrid items={recentItems} />
          )}
        </CardContent>
      </Card>

      {/* My Match Verifications */}
      <Card>
        <CardHeader>
          <CardTitle className="font-outfit text-xl flex items-center gap-2">
            <Shield className="w-5 h-5 text-emerald-600" />
            My Match Verifications
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="spinner" />
            </div>
          ) : myVerifications.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle2 className="w-12 h-12 mx-auto text-slate-300 mb-3" />
              <p className="text-slate-500">No verification requests yet</p>
            </div>
          ) : (
            <div className="space-y-4">
              {myVerifications.map((match) => (
                <div
                  key={match.id}
                  className="p-4 bg-slate-50 rounded-lg border border-slate-200 space-y-3 animate-fade-in"
                  data-testid={`match-verify-${match.id}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge className="bg-emerald-50 text-emerald-700">
                        {match.confidence_score}% Match
                      </Badge>
                      <span className="text-sm font-semibold text-slate-800">
                        Lost: {match.lost_item?.description} vs Found: {match.found_item?.description}
                      </span>
                    </div>
                    <Badge className={getMatchStatusColor(match.status)}>
                      {match.status.replace('_', ' ')}
                    </Badge>
                  </div>

                  {/* Verification Questions List */}
                  {match.questions && match.questions.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-200 space-y-3">
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                        Office Verification Interview
                      </p>
                      {match.questions.map((q, idx) => (
                        <div key={q.id} className="bg-white rounded-lg p-3 border border-slate-150 space-y-2 text-sm">
                          <p className="font-medium text-slate-700 flex items-start gap-1.5">
                            <span className="text-slate-400">Q:</span>
                            {q.question}
                          </p>
                          {q.answer ? (
                            <p className="text-slate-600 bg-slate-50 p-2 rounded border border-slate-100 flex items-start gap-1.5">
                              <span className="text-emerald-500 font-semibold">A:</span>
                              {q.answer}
                            </p>
                          ) : (
                            <div className="space-y-2 pt-1">
                              <textarea
                                placeholder="Type your answer to verify ownership..."
                                rows={2}
                                className="w-full rounded-md border border-slate-200 p-2 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400 resize-none"
                                id={`match-ans-input-${match.id}-${q.id}`}
                              />
                              <div className="flex justify-end">
                                <Button
                                  size="sm"
                                  onClick={() => {
                                    const inputEl = document.getElementById(`match-ans-input-${match.id}-${q.id}`);
                                    if (inputEl) {
                                      submitVerificationAnswer(match.id, q.id, inputEl.value);
                                      inputEl.value = '';
                                    }
                                  }}
                                  className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs h-8 px-3"
                                >
                                  Submit Answer
                                </Button>
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* My Claims */}
      <Card>
        <CardHeader>
          <CardTitle className="font-outfit text-xl">My Claims Status</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="spinner" />
            </div>
          ) : myClaims.length === 0 ? (
            <div className="text-center py-8">
              <CheckCircle2 className="w-12 h-12 mx-auto text-slate-300 mb-3" />
              <p className="text-slate-500">No claims yet</p>
            </div>
          ) : (
            <div className="space-y-4">
              {myClaims.map((claim) => (
                <div 
                  key={claim.id} 
                  className="p-4 bg-slate-50 rounded-lg border border-slate-100 space-y-3 animate-fade-in"
                  data-testid={`claim-${claim.id}`}
                >
                  <div className="flex items-center gap-4">
                    {claim.item?.image_url && (
                      <img 
                        src={`${process.env.REACT_APP_BACKEND_URL || 'https://lostnfound-clg-main.onrender.com'}${claim.item.image_url}`}
                        alt=""
                        className="w-16 h-16 rounded-lg object-cover"
                        onError={(e) => {
                          e.target.src = 'https://images.pexels.com/photos/3731256/pexels-photo-3731256.jpeg?auto=compress&cs=tinysrgb&w=100';
                        }}
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 truncate">
                        {claim.item?.description || 'Item'}
                      </p>
                      <p className="text-xs text-slate-500 mt-1">
                        Claimed on {new Date(claim.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <Badge className={getClaimStatusColor(claim.status)}>
                      {claim.status.replace('_', ' ')}
                    </Badge>
                  </div>
                  
                  {/* Verification Questions Section */}
                  {claim.verification_questions && claim.verification_questions.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-slate-200/60 space-y-3">
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                        Ownership Verification
                      </p>
                      {claim.verification_questions.map((q, idx) => {
                        const ans = claim.verification_answers?.[idx];
                        return (
                          <div key={q.id} className="bg-white rounded-lg p-3 border border-slate-200/50 space-y-2 text-sm">
                            <p className="font-medium text-slate-700 flex items-start gap-1.5">
                              <span className="text-slate-400">Q:</span>
                              {q.question}
                            </p>
                            {ans ? (
                              <p className="text-slate-600 bg-slate-50 p-2 rounded border border-slate-100 flex items-start gap-1.5">
                                <span className="text-emerald-500 font-semibold">A:</span>
                                {ans.answer}
                              </p>
                            ) : (
                              <div className="space-y-2 pt-1">
                                <textarea
                                  placeholder="Type your answer to verify ownership..."
                                  rows={2}
                                  className="w-full rounded-md border border-slate-200 p-2 text-sm focus:outline-none focus:ring-1 focus:ring-slate-400 resize-none"
                                  id={`ans-input-${claim.id}-${idx}`}
                                />
                                <div className="flex justify-end">
                                  <Button
                                    size="sm"
                                    onClick={() => {
                                      const inputEl = document.getElementById(`ans-input-${claim.id}-${idx}`);
                                      if (inputEl) {
                                        submitAnswer(claim.id, inputEl.value);
                                        inputEl.value = '';
                                      }
                                    }}
                                    className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs h-8 px-3"
                                  >
                                    Submit Answer
                                  </Button>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default StudentDashboard;
