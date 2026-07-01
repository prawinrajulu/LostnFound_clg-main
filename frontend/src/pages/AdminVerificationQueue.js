import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { verificationAPI } from '../services/api';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { Shield, ArrowRight, RefreshCw, MessageSquare, MapPin, Calendar } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'https://lostnfound-clg-main.onrender.com';

const AdminVerificationQueue = () => {
  const navigate = useNavigate();
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState('all');

  useEffect(() => {
    fetchQueue();
  }, []);

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const response = await verificationAPI.getQueue();
      setQueue(response.data || []);
    } catch (error) {
      console.error('Failed to fetch queue:', error);
      toast.error('Failed to load verification queue');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'pending':
        return <Badge className="bg-yellow-100 text-yellow-800 border-yellow-200">Pending</Badge>;
      case 'student_notified':
        return <Badge className="bg-blue-100 text-blue-800 border-blue-200">Student Notified</Badge>;
      case 'verification_started':
        return <Badge className="bg-blue-100 text-blue-800 border-blue-200">Verification Started</Badge>;
      case 'qa_completed':
        return <Badge className="bg-blue-100 text-blue-800 border-blue-200">Q&A Completed</Badge>;
      case 'approved':
        return <Badge className="bg-emerald-100 text-emerald-800 border-emerald-200">Approved</Badge>;
      case 'rejected':
        return <Badge className="bg-rose-100 text-rose-800 border-rose-200">Rejected</Badge>;
      case 'completed':
        return <Badge className="bg-slate-100 text-slate-800 border-slate-200">Completed</Badge>;
      default:
        return <Badge className="bg-slate-100 text-slate-800">{status}</Badge>;
    }
  };

  const filteredQueue = queue.filter(item => {
    if (filterStatus === 'all') return true;
    if (filterStatus === 'active') {
      return ['pending', 'student_notified', 'verification_started', 'qa_completed'].includes(item.status);
    }
    return item.status === filterStatus;
  });

  return (
    <div className="space-y-6 animate-fade-in" data-testid="admin-verification-queue">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-outfit text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Shield className="w-6 h-6 text-emerald-600" />
            Verification Queue
          </h1>
          <p className="text-slate-500">
            Verify ownership and manage release flows for matching items
          </p>
        </div>
        <Button 
          onClick={fetchQueue} 
          disabled={loading}
          variant="outline"
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-4">
        {[
          { id: 'all', label: 'All' },
          { id: 'active', label: 'Active Queue' },
          { id: 'approved', label: 'Approved' },
          { id: 'rejected', label: 'Rejected' },
          { id: 'completed', label: 'Completed' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setFilterStatus(tab.id)}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
              filterStatus === tab.id
                ? 'bg-slate-900 text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex flex-col items-center justify-center py-16">
          <div className="spinner mb-4" />
          <p className="text-slate-500 font-medium">Loading queue items...</p>
        </div>
      ) : filteredQueue.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Shield className="w-12 h-12 mx-auto text-slate-300 mb-4" />
            <p className="text-slate-500 font-medium">No matches in queue</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredQueue.map((item) => (
            <Card key={item.id} className="card-hover overflow-hidden border border-slate-200">
              <CardContent className="p-6">
                <div className="flex items-center justify-between mb-4 pb-4 border-b border-slate-100">
                  <div className="flex items-center gap-3">
                    {getStatusBadge(item.status)}
                    <Badge className="bg-emerald-50 text-emerald-700 hover:bg-emerald-50">
                      {item.confidence_score}% Match
                    </Badge>
                  </div>
                  <span className="text-xs text-slate-400">
                    Detected {new Date(item.created_at).toLocaleDateString()}
                  </span>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-[1fr,auto,1fr] gap-6 items-center">
                  {/* Lost Item */}
                  <div className="bg-orange-50/50 border border-orange-100 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                      <Badge className="status-lost">LOST ITEM</Badge>
                      <span className="text-xs font-semibold text-slate-700">
                        {item.lost_item?.student?.full_name} ({item.lost_item?.student?.roll_number})
                      </span>
                    </div>
                    <div className="flex gap-4">
                      <img
                        src={item.lost_item?.image_url ? `${BACKEND_URL}${item.lost_item.image_url}` : 'https://images.pexels.com/photos/3731256/pexels-photo-3731256.jpeg?auto=compress&cs=tinysrgb&w=100'}
                        alt=""
                        className="w-16 h-16 rounded-lg object-cover"
                        onError={(e) => {
                          e.target.src = 'https://images.pexels.com/photos/3731256/pexels-photo-3731256.jpeg?auto=compress&cs=tinysrgb&w=100';
                        }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-slate-800 line-clamp-1">{item.lost_item?.description}</p>
                        <div className="mt-2 space-y-1 text-xs text-slate-500">
                          <p className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5" />{item.lost_item?.location}</p>
                          <p className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" />{item.lost_item?.created_date}</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Connector Arrow */}
                  <div className="flex justify-center">
                    <div className="w-10 h-10 bg-slate-100 rounded-full flex items-center justify-center border border-slate-200">
                      <ArrowRight className="w-5 h-5 text-slate-400" />
                    </div>
                  </div>

                  {/* Found Item */}
                  <div className="bg-emerald-50/50 border border-emerald-100 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                      <Badge className="status-found">FOUND ITEM</Badge>
                      <span className="text-xs font-semibold text-slate-700">
                        {item.found_item?.student?.full_name} ({item.found_item?.student?.roll_number})
                      </span>
                    </div>
                    <div className="flex gap-4">
                      <img
                        src={item.found_item?.image_url ? `${BACKEND_URL}${item.found_item.image_url}` : 'https://images.pexels.com/photos/3731256/pexels-photo-3731256.jpeg?auto=compress&cs=tinysrgb&w=100'}
                        alt=""
                        className="w-16 h-16 rounded-lg object-cover"
                        onError={(e) => {
                          e.target.src = 'https://images.pexels.com/photos/3731256/pexels-photo-3731256.jpeg?auto=compress&cs=tinysrgb&w=100';
                        }}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-slate-800 line-clamp-1">{item.found_item?.description}</p>
                        <div className="mt-2 space-y-1 text-xs text-slate-500">
                          <p className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5" />{item.found_item?.location}</p>
                          <p className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" />{item.found_item?.created_date}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-slate-100 flex justify-end">
                  <Button
                    onClick={() => navigate(`/admin/verification-session/${item.id}`)}
                    className="bg-slate-900 hover:bg-slate-800 text-white"
                  >
                    <MessageSquare className="w-4 h-4 mr-2" />
                    Enter Verification Q&A
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default AdminVerificationQueue;
